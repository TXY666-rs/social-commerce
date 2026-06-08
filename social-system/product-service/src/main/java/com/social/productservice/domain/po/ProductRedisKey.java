package com.social.productservice.domain.po;

import java.util.Arrays;
import java.util.List;

public class ProductRedisKey {

    //商品分类缓存key
    public static final String PRODUCT_CATEGORIES = "product:categories:";
    //商品详细key
    public static final String CACHE_PRODUCT_DETAIL = "product:detail:";
    //商品列表key
    public static final String CACHE_PRODUCT_LIST_PAGE = "product:list:page";
    //商品卖家key
    public static final String CACHE_SELLER_PRODUCTS = "product:seller:";
    //按分类查询商品缓存key
    public static final String CACHE_PRODUCT_CATEGORY = "product:category:";
    public static final String CACHE_PRODUCT_CATEGORY_LOCK = "product:category:lock:";
    public static final List<String> DEFAULT_CATEGORIES = Arrays.asList(
            "男装服饰", "女装服饰", "家用电器", "游戏外设", "鞋", "手机数码", "电脑办公", "美妆护肤", "平板数码", "其他"
    );
    // ========== 缓存过期时间 ==========
    public static final long DETAIL_TTL = 30;    // 商品详情30分钟
    public static final long LIST_TTL = 5;        // 列表5分钟
    public static final long CATEGORIES_TTL = 60; // 分类1小时
    public static final long CATEGORY_PRODUCT_TTL = 5; // 分类商品5分钟
    public static final long CACHE_PRODUCT_LOCK_TTL = 10;

    // ========== 锁名称 ==========
    public static final String CACHE_PRODUCT_LIST_PAGE_LOCK = "product:list:page:lock:";
    public static final String CACHE_PRODUCT_LOCK = "product:lock:";
}
