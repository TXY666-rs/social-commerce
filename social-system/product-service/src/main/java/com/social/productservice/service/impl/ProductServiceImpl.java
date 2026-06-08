package com.social.productservice.service.impl;

import cn.hutool.core.lang.TypeReference;
import cn.hutool.json.JSONUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.social.productservice.domain.dto.*;
import com.social.productservice.domain.po.Category;
import com.social.productservice.domain.po.Product;
import com.social.productservice.domain.vo.AgentResponse;
import com.social.productservice.domain.vo.ProductListVO;
import com.social.productservice.domain.vo.ProductVO;
import com.social.productservice.domain.vo.ToAgentProductVO;
import com.social.productservice.mapper.CategoryMapper;
import com.social.productservice.mapper.ProductMapper;
import com.social.productservice.service.ProductService;
import com.social.socialcommon.result.Result;
import com.social.socialcommon.utils.RedisUtil;
import com.social.user.service.api.dto.UserBriefDTO;
import com.social.user.service.api.feign.UserClient;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;


import java.util.Arrays;
import java.util.Collections;
import java.util.concurrent.TimeUnit;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import static com.social.productservice.domain.po.ProductRedisKey.*;

/**
 * 商品服务实现类
 * 二手市场模式 + Redis缓存
 */
@Slf4j
@Service
public class ProductServiceImpl implements ProductService {

    @Autowired
    private RedisUtil redisUtil;

    @Autowired
    private ProductMapper productMapper;

    @Autowired
    private CategoryMapper categoryMapper;

    @Autowired
    private UserClient userClient;

    /**
     * OSS URL前缀，用于拼接相对路径的图片地址
     * 从Nacos配置 (social-common) 读取
     */
    @Value("${aliyun.oss.url-prefix:}")
    private String ossUrlPrefix;



    @Override
    @Transactional
    public ProductVO createProduct(Long sellerId, ProductCreateDTO createDTO) {
        Product product = new Product();
        BeanUtils.copyProperties(createDTO, product);

        product.setSellerId(sellerId);
        product.setStatus(1);
        product.setViewCount(0);
        product.setStock(1); // 二手物品默认只有1件
        // 将 categories 列表转为逗号分隔字符串存入 category
        if (createDTO.getCategories() != null && !createDTO.getCategories().isEmpty()) {
            validateCategories(createDTO.getCategories());
            product.setCategory(String.join(",", createDTO.getCategories()));
        }
        // 将 deliveryTypes 列表转为逗号分隔字符串存入 deliveryType
        if (createDTO.getDeliveryTypes() != null && !createDTO.getDeliveryTypes().isEmpty()) {
            product.setDeliveryType(createDTO.getDeliveryTypes().stream()
                    .map(String::valueOf)
                    .collect(Collectors.joining(",")));
        } else {
            product.setDeliveryType("1"); // 默认支持快递发货
        }

        // 延迟双删：先删缓存
        clearListCache();
        clearSellerCache(sellerId);
        clearCategoryCache();

        productMapper.insert(product);
        log.info("商品创建成功，ID: {}, 卖家: {}", product.getId(), sellerId);

        return convertToProductVO(product);
    }

    @Override
    @Transactional
    public ProductVO updateProduct(Long productId, Long sellerId, ProductUpdateDTO updateDTO) {
        Product product = productMapper.selectById(productId);
        if (product == null) {
            throw new RuntimeException("商品不存在");
        }
        if (!product.getSellerId().equals(sellerId)) {
            throw new RuntimeException("无权修改该商品");
        }

        if (updateDTO.getName() != null) product.setName(updateDTO.getName());
        if (updateDTO.getDescription() != null) product.setDescription(updateDTO.getDescription());
        if (updateDTO.getPrice() != null) product.setPrice(updateDTO.getPrice());
        if (updateDTO.getStock() != null) product.setStock(updateDTO.getStock());
        if (updateDTO.getCategories() != null) {
            validateCategories(updateDTO.getCategories());
            product.setCategory(String.join(",", updateDTO.getCategories()));
        }
        if (updateDTO.getDeliveryTypes() != null) {
            product.setDeliveryType(updateDTO.getDeliveryTypes().stream()
                    .map(String::valueOf)
                    .collect(Collectors.joining(",")));
        }
        if (updateDTO.getImage() != null) product.setImage(updateDTO.getImage());

        if (updateDTO.getStatus() != null) {
            if (updateDTO.getStatus() != 0 && updateDTO.getStatus() != 1) {
                throw new RuntimeException("状态值无效，只能为0(下架)或1(上架)");
            }
            product.setStatus(updateDTO.getStatus());
        }

        // 延迟双删：先删缓存
        clearDetailCache(productId);
        clearListCache();
        clearSellerCache(sellerId);
        clearCategoryCache();

        productMapper.updateById(product);
        log.info("商品更新成功，ID: {}", productId);

        return convertToProductVO(product);
    }

    @Override
    @Transactional
    public boolean deleteProduct(Long productId, Long sellerId) {
        Product product = productMapper.selectById(productId);
        if (product == null) {
            throw new RuntimeException("商品不存在");
        }
        // sellerId == null 表示管理员操作，跳过卖家校验
        if (sellerId != null && !product.getSellerId().equals(sellerId)) {
            throw new RuntimeException("无权删除该商品");
        }

        // 延迟双删：先删缓存
        clearDetailCache(productId);
        clearListCache();
        clearSellerCache(sellerId);
        clearCategoryCache();

        return productMapper.deleteById(productId) > 0;
    }

    @Override
    public ProductVO getProductDetail(Long productId) {
        // 先查缓存
        String productKey = CACHE_PRODUCT_DETAIL + productId;
        String productJson = redisUtil.get(productKey);
        if (productJson != null && !productJson.trim().isEmpty()) {
            // 空值标记，避免缓存穿透
            if ("null".equals(productJson)) {
                throw new RuntimeException("商品不存在");
            }
            return JSONUtil.toBean(productJson, ProductVO.class);
        }

        // 尝试获取分布式锁（只试一次，不阻塞线程）
        String productLock = CACHE_PRODUCT_LOCK + productId;
        boolean isLock = redisUtil.tryLock(productLock, CACHE_PRODUCT_LOCK_TTL, TimeUnit.SECONDS);
        if (isLock) {
            try {
                // Double-check 缓存
                String productJsonAgain = redisUtil.get(productKey);
                if (productJsonAgain != null && !productJsonAgain.trim().isEmpty()) {
                    if ("null".equals(productJsonAgain)) {
                        throw new RuntimeException("商品不存在");
                    }
                    return JSONUtil.toBean(productJsonAgain, ProductVO.class);
                }
                // 查数据库并回填缓存
                Product product = productMapper.selectById(productId);
                if (product == null) {
                    redisUtil.set(productKey, "null", 1, TimeUnit.MINUTES);
                    throw new RuntimeException("商品不存在");
                }
                productMapper.incrementViewCount(productId);
                ProductVO productVO = convertToProductVO(product);
                redisUtil.set(productKey, JSONUtil.toJsonStr(productVO), DETAIL_TTL, TimeUnit.SECONDS);
                return productVO;
            } finally {
                redisUtil.delete(productLock);
            }
        }

        // 未获取锁，直接查数据库（避免 Thread.sleep 阻塞线程）
        Product product = productMapper.selectById(productId);
        if (product == null) {
            throw new RuntimeException("商品不存在");
        }
        return convertToProductVO(product);
    }

    @Override
    public IPage<ProductListVO> getProductPage(ProductQueryDTO queryDTO) throws InterruptedException {
        // 缓存key包含所有查询条件，避免不同查询互相覆盖
        String cacheKeySuffix = buildListCacheKeySuffix(queryDTO);
        String key = CACHE_PRODUCT_LIST_PAGE + cacheKeySuffix;
        String cached = redisUtil.get(key);
        if (cached != null && !cached.trim().isEmpty()) {
            log.debug("商品列表命中缓存, key={}", key);
            return JSONUtil.toBean(cached, new TypeReference<Page<ProductListVO>>() {}, false);
        }
        //  查数据库，先获取锁。
        String lockKey = CACHE_PRODUCT_LIST_PAGE_LOCK + cacheKeySuffix;
        int maxRetry = 20;
        for (int i = 0; i < maxRetry; i++) {
            boolean lock = redisUtil.tryLock(lockKey, CACHE_PRODUCT_LOCK_TTL, TimeUnit.SECONDS);
            if (lock) {
                try {
                    // 再查一次redis，可能缓存已经重建
                    String tryAgain = redisUtil.get(key);
                    if (tryAgain != null && !tryAgain.trim().isEmpty()) {
                        return JSONUtil.toBean(tryAgain, new TypeReference<Page<ProductListVO>>() {}, false);
                    }
                    // 查数据库
                    Page<ProductListVO> page = new Page<>(queryDTO.getPageNum(), queryDTO.getPageSize());
                    IPage<ProductListVO> productListVOPage = productMapper.selectProductPage(
                            page, queryDTO.getCategory(), queryDTO.getKeyword(), queryDTO.getStatus() != null ? queryDTO.getStatus() : 1
                    );
                    redisUtil.set(key, JSONUtil.toJsonStr(productListVOPage), LIST_TTL, TimeUnit.MINUTES);
                    log.debug("商品列表写入缓存, key={}", key);
                    return productListVOPage;
                } finally {
                    redisUtil.delete(lockKey);
                }
            } else {
                Thread.sleep(50);
            }
        }
        // 重试耗尽，直接查数据库
        Page<ProductListVO> page = new Page<>(queryDTO.getPageNum(), queryDTO.getPageSize());
        IPage<ProductListVO> productListVOPage = productMapper.selectProductPage(
                page, queryDTO.getCategory(), queryDTO.getKeyword(), queryDTO.getStatus() != null ? queryDTO.getStatus() : 1
        );
        return productListVOPage;
    }

    /**
     * 构建列表缓存key后缀，包含所有查询条件
     */
    private String buildListCacheKeySuffix(ProductQueryDTO queryDTO) {
        StringBuilder sb = new StringBuilder();
        sb.append(":p").append(queryDTO.getPageNum());
        sb.append(":s").append(queryDTO.getPageSize());
        if (queryDTO.getCategory() != null && !queryDTO.getCategory().isEmpty()) {
            sb.append(":c").append(queryDTO.getCategory());
        }
        if (queryDTO.getKeyword() != null && !queryDTO.getKeyword().isEmpty()) {
            sb.append(":k").append(queryDTO.getKeyword());
        }
        if (queryDTO.getStatus() != null) {
            sb.append(":st").append(queryDTO.getStatus());
        }
        return sb.toString();
    }

    @Override
    public IPage<ProductVO> getSellerProducts(Long sellerId, ProductQueryDTO queryDTO) {
//        String cacheKey = buildListCacheKey(queryDTO, sellerId);
//        IPage<ProductVO> cached = redisUtil.getObject(cacheKey, new TypeReference<IPage<ProductVO>>() {});
//        if (cached != null) {
//            log.debug("卖家商品列表命中缓存, key={}", cacheKey);
//            return cached;
//        }

        Page<Product> page = new Page<>(queryDTO.getPageNum(), queryDTO.getPageSize());
        IPage<Product> productPage = productMapper.selectSellerProductPage(
                page, sellerId, queryDTO.getCategory(), queryDTO.getKeyword(), queryDTO.getStatus()
        );
        
        // 批量预加载卖家昵称，避免 N+1
        List<Long> sellerIds = productPage.getRecords().stream()
                .map(Product::getSellerId)
                .filter(id -> id != null)
                .distinct()
                .toList();
        Map<Long, UserBriefDTO> userMap = Collections.emptyMap();
        if (!sellerIds.isEmpty()) {
            Result<Map<Long, UserBriefDTO>> batchResult = userClient.batchGetUserBrief(sellerIds);
            if (batchResult != null && batchResult.getData() != null) {
                userMap = batchResult.getData();
            }
        }
        final Map<Long, UserBriefDTO> finalUserMap = userMap;
        
        IPage<ProductVO> result = productPage.convert(p -> convertToProductVO(p, finalUserMap));

//        // 卖家商品列表缓存时间短一些
//        redisUtil.setObject(cacheKey, result, 3, TimeUnit.MINUTES);

        return result;
    }

    @Override
    @Transactional
    public boolean toggleProductStatus(Long productId, Long sellerId, Integer status) {
        if (status != 0 && status != 1) {
            throw new RuntimeException("状态值无效，只能为0(下架)或1(上架)");
        }
        Product product = productMapper.selectById(productId);
        if (product == null) {
            throw new RuntimeException("商品不存在");
        }
        // sellerId == null 表示管理员操作，跳过卖家校验
        if (sellerId != null && !product.getSellerId().equals(sellerId)) {
            throw new RuntimeException("无权操作该商品");
        }

        product.setStatus(status);

        // 延迟双删：先删缓存
        clearDetailCache(productId);
        clearListCache();
        clearSellerCache(sellerId);
        clearCategoryCache();

        return productMapper.updateById(product) > 0;
    }

    @Override
    public List<ProductListVO> getProductsByCategory(String category) throws InterruptedException {
        String key = CACHE_PRODUCT_CATEGORY + category;
        String cached = redisUtil.get(key);
        if (cached != null && !cached.trim().isEmpty()) {
            log.debug("分类商品命中缓存, key={}", key);
            return JSONUtil.toList(cached, ProductListVO.class);
        }

        String lockKey = CACHE_PRODUCT_CATEGORY_LOCK + category;
        int maxRetry = 20;
        for (int i = 0; i < maxRetry; i++) {
            boolean lock = redisUtil.tryLock(lockKey, CACHE_PRODUCT_LOCK_TTL, TimeUnit.SECONDS);
            if (lock) {
                try {
                    // double-check
                    String cachedAgain = redisUtil.get(key);
                    if (cachedAgain != null && !cachedAgain.trim().isEmpty()) {
                        return JSONUtil.toList(cachedAgain, ProductListVO.class);
                    }

                    List<ProductListVO> list = productMapper.selectByCategory(category);
                    if (list != null && !list.isEmpty()) {
                        redisUtil.set(key, JSONUtil.toJsonStr(list), CATEGORY_PRODUCT_TTL, TimeUnit.MINUTES);
                    } else {
                        redisUtil.set(key, "[]", 1, TimeUnit.MINUTES);
                    }
                    return list;
                } finally {
                    redisUtil.delete(lockKey);
                }
            } else {
                Thread.sleep(50);
            }
        }
        // 重试耗尽，直接查数据库
        return productMapper.selectByCategory(category);
    }

    @Override
    public List<String> getCategories() {
        // 先查缓存
        String categoriesJson = redisUtil.get(PRODUCT_CATEGORIES);
        if (categoriesJson != null) {
            return JSONUtil.toList(categoriesJson, String.class);
        }
        // 从数据库读取启用的分类
        LambdaQueryWrapper<Category> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Category::getStatus, 1)
               .orderByAsc(Category::getSortOrder)
               .orderByDesc(Category::getCreateTime);
        List<Category> categories = categoryMapper.selectList(wrapper);
        List<String> names = categories.stream().map(Category::getName).collect(Collectors.toList());

        // 如果数据库没有分类，返回默认分类（兼容初始化阶段）
        if (names.isEmpty()) {
            names = DEFAULT_CATEGORIES;
        }

        redisUtil.set(PRODUCT_CATEGORIES, JSONUtil.toJsonStr(names), CATEGORIES_TTL, TimeUnit.MINUTES);
        return names;
    }


    /**
     * 延迟双删：立即删除 + 延迟 500ms 再删一次
     */
    private void clearDetailCache(Long productId) {
        String key = CACHE_PRODUCT_DETAIL + productId;
        redisUtil.delete(key);
        redisUtil.deleteAsync(key, 500);
    }

    /**
     * 延迟双删：清除商品列表缓存
     */
    private void clearListCache() {
        String pattern = CACHE_PRODUCT_LIST_PAGE + "*";
        redisUtil.deleteByPattern(pattern);
        redisUtil.deleteByPatternAsync(pattern, 500);
    }

    /**
     * 延迟双删：清除卖家商品列表缓存
     */
    private void clearSellerCache(Long sellerId) {
        String pattern = CACHE_SELLER_PRODUCTS + sellerId + ":*";
        redisUtil.deleteByPattern(pattern);
        redisUtil.deleteByPatternAsync(pattern, 500);
    }

    /**
     * 延迟双删：清除分类商品缓存
     */
    private void clearCategoryCache() {
        String pattern = CACHE_PRODUCT_CATEGORY + "*";
        redisUtil.deleteByPattern(pattern);
        redisUtil.deleteByPatternAsync(pattern, 500);
    }

    // ========== 转换方法 ==========

    /**
     * 转换Product到ProductVO
     */
    private ProductVO convertToProductVO(Product product) {
        return convertToProductVO(product, Collections.emptyMap());
    }

    private ProductVO convertToProductVO(Product product, Map<Long, UserBriefDTO> userMap) {
        ProductVO vo = new ProductVO();
        BeanUtils.copyProperties(product, vo);

        // 将 category 逗号分隔字符串转为 categories 列表
        vo.setCategories(parseCategoryList(product.getCategory()));

        // 将 deliveryType 逗号分隔字符串转为 deliveryTypes 列表
        vo.setDeliveryTypes(parseDeliveryTypeList(product.getDeliveryType()));

        // 拼接图片完整URL列表
        vo.setImages(resolveImageUrls(product.getImage()));

        // 查询卖家昵称：优先从预加载 Map 获取，兜底单独查询
        if (product.getSellerId() != null) {
            UserBriefDTO userBriefDTO = userMap.get(product.getSellerId());
            if (userBriefDTO == null) {
                userBriefDTO = userClient.getUserBrief(product.getSellerId()).getData();
            }
            if (userBriefDTO != null) {
                vo.setSellerNickname(userBriefDTO.getUsername());
            }
        }

        return vo;
    }

    /**
     * 将逗号分隔的分类字符串转为列表
     */
    private List<String> parseCategoryList(String category) {
        if (category == null || category.trim().isEmpty()) {
            return Collections.emptyList();
        }
        return Arrays.stream(category.split(","))
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .collect(Collectors.toList());
    }

    /**
     * 将逗号分隔的配送方式字符串转为列表
     */
    private List<Integer> parseDeliveryTypeList(String deliveryType) {
        if (deliveryType == null || deliveryType.trim().isEmpty()) {
            return Collections.emptyList();
        }
        return Arrays.stream(deliveryType.split(","))
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .map(Integer::parseInt)
                .collect(Collectors.toList());
    }

    /**
     * 解析图片URL：将逗号分隔的图片字段转为完整URL列表
     * 完整URL（以http开头）原样保留，相对路径拼接OSS前缀
     */
    private List<String> resolveImageUrls(String image) {
        if (image == null || image.trim().isEmpty()) {
            return Collections.emptyList();
        }
        return Arrays.stream(image.split(","))
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .map(url -> {
                    // 已经是完整URL，直接返回
                    if (url.startsWith("http://") || url.startsWith("https://")) {
                        return url;
                    }
                    // 相对路径，拼接OSS前缀
                    if (StringUtils.hasText(ossUrlPrefix)) {
                        return ossUrlPrefix + "/" + url;
                    }
                    // 无前缀配置时原样返回（兼容旧数据）
                    return url;
                })
                .collect(Collectors.toList());
    }

    // ========== 分类管理 ==========

    @Override
    public List<Category> getAllCategories() {
        LambdaQueryWrapper<Category> wrapper = new LambdaQueryWrapper<>();
        wrapper.orderByAsc(Category::getSortOrder).orderByDesc(Category::getCreateTime);
        return categoryMapper.selectList(wrapper);
    }

    @Override
    @Transactional
    public void addCategory(String name, Integer sortOrder) {
        // 检查重名
        LambdaQueryWrapper<Category> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Category::getName, name);
        if (categoryMapper.selectCount(wrapper) > 0) {
            throw new RuntimeException("分类名称已存在");
        }
        Category category = new Category();
        category.setName(name);
        category.setSortOrder(sortOrder != null ? sortOrder : 0);
        category.setStatus(1);
        // 延迟双删：先删缓存
        String catKey = PRODUCT_CATEGORIES;
        redisUtil.delete(catKey);
        redisUtil.deleteAsync(catKey, 500);
        categoryMapper.insert(category);
    }

    @Override
    @Transactional
    public void updateCategory(Long id, String name, Integer sortOrder, Integer status) {
        Category category = categoryMapper.selectById(id);
        if (category == null) {
            throw new RuntimeException("分类不存在");
        }
        if (name != null) category.setName(name);
        if (sortOrder != null) category.setSortOrder(sortOrder);
        if (status != null) category.setStatus(status);
        // 延迟双删：先删缓存
        String catKey = PRODUCT_CATEGORIES;
        redisUtil.delete(catKey);
        redisUtil.deleteAsync(catKey, 500);
        categoryMapper.updateById(category);
    }

    @Override
    @Transactional
    public void deleteCategory(Long id) {
        Category category = categoryMapper.selectById(id);
        if (category == null) {
            throw new RuntimeException("分类不存在");
        }
        // 延迟双删：先删缓存
        String catKey = PRODUCT_CATEGORIES;
        redisUtil.delete(catKey);
        redisUtil.deleteAsync(catKey, 500);
        categoryMapper.deleteById(id);
    }


    @Override
    public AgentResponse getProductVOList(ProductAgentQueryDTO productAgentQueryDTO) {
        List<ToAgentProductVO> productList = productMapper.selectByScalarQuery(
                productAgentQueryDTO.getCategory(),
                productAgentQueryDTO.getKeyword(),
                productAgentQueryDTO.getTop_k(),
                productAgentQueryDTO.getMin_price(),
                productAgentQueryDTO.getStatus(),
                productAgentQueryDTO.getMax_price());

        AgentResponse agentResponse = new AgentResponse();
        agentResponse.setAgentProductVOList(productList);
        agentResponse.setTotal(productList.size());
        return agentResponse;
    }

    /**
     * 校验分类列表中的每个分类是否存在于数据库中
     */
    private void validateCategories(List<String> categories) {
        if (categories == null || categories.isEmpty()) {
            return;
        }
        // 获取所有有效分类名
        LambdaQueryWrapper<Category> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Category::getStatus, 1);
        List<Category> validCategories = categoryMapper.selectList(wrapper);

        // 如果数据库没有分类（初始化阶段），跳过校验
        if (validCategories.isEmpty()) {
            return;
        }

        java.util.Set<String> validNames = validCategories.stream()
                .map(Category::getName)
                .collect(Collectors.toSet());

        for (String cat : categories) {
            if (!validNames.contains(cat)) {
                throw new RuntimeException("无效的分类: " + cat);
            }
        }
    }

}
