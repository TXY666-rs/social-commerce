package com.social.couponservice.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.TypeReference;
import com.social.couponservice.domain.dto.CouponCreateDTO;
import com.social.couponservice.domain.po.Coupon;
import com.social.couponservice.domain.po.CouponRedisKey;
import com.social.couponservice.domain.po.UserCoupon;
import com.social.couponservice.domain.vo.CouponVO;
import com.social.couponservice.domain.vo.UserCouponVO;
import com.social.couponservice.mapper.CouponMapper;
import com.social.couponservice.mapper.UserCouponMapper;
import com.social.couponservice.service.CouponService;
import com.social.socialcommon.utils.RedisUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

/**
 * 优惠券服务实现
 */
@Slf4j
@Service
public class CouponServiceImpl extends ServiceImpl<CouponMapper, Coupon> implements CouponService {

    @Autowired
    private CouponMapper couponMapper;

    @Autowired
    private UserCouponMapper userCouponMapper;

    @Autowired
    private RedisUtil redisUtil;

    // ========== 管理员端 ==========

    @Override
    public List<CouponVO> getCouponList(String name, Integer status) {
        LambdaQueryWrapper<Coupon> wrapper = new LambdaQueryWrapper<>();
        if (name != null && !name.isEmpty()) {
            wrapper.like(Coupon::getName, name);
        }
        if (status != null) {
            wrapper.eq(Coupon::getStatus, status);
        }
        wrapper.orderByDesc(Coupon::getCreateTime);

        List<Coupon> list = couponMapper.selectList(wrapper);
        return list.stream().map(coupon -> BeanUtil.copyProperties(coupon, CouponVO.class)).collect(Collectors.toList());
    }

    @Override
    public CouponVO getCouponDetail(Long id) {
        String cacheKey = CouponRedisKey.COUPON_DETAIL + id;
        String cached = redisUtil.get(cacheKey);
        if (cached != null) {
            return JSON.parseObject(cached, CouponVO.class);
        }

        String lockKey = CouponRedisKey.COUPON_DETAIL_LOCK + id;
        if (redisUtil.tryLock(lockKey, 10, TimeUnit.SECONDS)) {
            try {
                cached = redisUtil.get(cacheKey);
                if (cached != null) {
                    return JSON.parseObject(cached, CouponVO.class);
                }
                Coupon coupon = couponMapper.selectById(id);
                if (coupon == null) {
                    throw new RuntimeException("优惠券不存在");
                }
                CouponVO vo = BeanUtil.copyProperties(coupon, CouponVO.class);
                redisUtil.set(cacheKey, JSON.toJSONString(vo), CouponRedisKey.DETAIL_TTL, TimeUnit.MINUTES);
                return vo;
            } finally {
                redisUtil.delete(lockKey);
            }
        }
        Coupon coupon = couponMapper.selectById(id);
        if (coupon == null) {
            throw new RuntimeException("优惠券不存在");
        }
        return BeanUtil.copyProperties(coupon, CouponVO.class);
    }

    @Override
    public Long createCoupon(CouponCreateDTO dto) {
        Coupon coupon = new Coupon();
        BeanUtils.copyProperties(dto, coupon);
        coupon.setStatus(dto.getStatus() != null ? dto.getStatus() : 1); // 默认启用

        // 默认值
        if (coupon.getPerUserLimit() == null)
            coupon.setPerUserLimit(1);

        if (coupon.getTotalStock() == null){
            throw new RuntimeException("优惠卷总数不能为空");
        }
        // 延迟双删：先删缓存
        evictAvailableCache();
        coupon.setCreateTime(LocalDateTime.now());
        couponMapper.insert(coupon);
        log.info("[优惠券] 创建成功: id={}, name={}", coupon.getId(), coupon.getName());
        return coupon.getId();
    }

    @Override
    public void updateCoupon(Long id, CouponCreateDTO dto) {
        Coupon existing = couponMapper.selectById(id);
        if (existing == null) {
            throw new RuntimeException("优惠券不存在");
        }

        Coupon coupon = new Coupon();
        BeanUtils.copyProperties(dto, coupon);
        coupon.setId(id);
        coupon.setUpdateTime(LocalDateTime.now());

        // 保留不可改字段
        if (dto.getStatus() == null) coupon.setStatus(existing.getStatus());
        if (dto.getTotalStock() == null) coupon.setTotalStock(existing.getTotalStock());

        // 延迟双删：先删缓存
        evictCouponCache(id);
        evictAvailableCache();
        couponMapper.updateById(coupon);
        log.info("[优惠券] 更新成功: id={}", id);
    }

    @Override
    public void deleteCoupon(Long id) {
        Coupon existing = couponMapper.selectById(id);
        if (existing == null) {
            throw new RuntimeException("优惠券不存在");
        }
        // 延迟双删：先删缓存
        evictCouponCache(id);
        evictAvailableCache();
        couponMapper.deleteById(id);
        log.info("[优惠券] 删除成功: id={}", id);
    }

    // ========== 用户端 ==========

    @Override
    public List<CouponVO> getAvailableCoupons(Long userId) {
        // 缓存优惠券列表（不含用户领取信息）
        String cacheKey = CouponRedisKey.COUPON_AVAILABLE_LIST;
        List<CouponVO> result;

        String cached = redisUtil.get(cacheKey);
        if (cached != null) {
            result = JSON.parseObject(cached, new TypeReference<List<CouponVO>>() {});
        } else {
            String lockKey = CouponRedisKey.COUPON_AVAILABLE_LOCK;
            if (redisUtil.tryLock(lockKey, 10, TimeUnit.SECONDS)) {
                try {
                    cached = redisUtil.get(cacheKey);
                    if (cached != null) {
                        result = JSON.parseObject(cached, new TypeReference<List<CouponVO>>() {});
                    } else {
                        LambdaQueryWrapper<Coupon> wrapper = new LambdaQueryWrapper<>();
                        wrapper.eq(Coupon::getStatus, 1)
                               .ge(Coupon::getEndTime, LocalDateTime.now())
                               .gt(Coupon::getTotalStock, 0)
                               .orderByAsc(Coupon::getEndTime)
                               .orderByDesc(Coupon::getCreateTime);
                        List<Coupon> coupons = couponMapper.selectList(wrapper);
                        result = coupons.stream()
                                .map(c -> BeanUtil.copyProperties(c, CouponVO.class))
                                .collect(Collectors.toList());
                        redisUtil.set(cacheKey, JSON.toJSONString(result), CouponRedisKey.AVAILABLE_TTL, TimeUnit.MINUTES);
                    }
                } finally {
                    redisUtil.delete(lockKey);
                }
            } else {
                // 获取锁失败，直接查库
                LambdaQueryWrapper<Coupon> wrapper = new LambdaQueryWrapper<>();
                wrapper.eq(Coupon::getStatus, 1)
                       .ge(Coupon::getEndTime, LocalDateTime.now())
                       .gt(Coupon::getTotalStock, 0)
                       .orderByAsc(Coupon::getEndTime)
                       .orderByDesc(Coupon::getCreateTime);
                List<Coupon> coupons = couponMapper.selectList(wrapper);
                result = coupons.stream()
                        .map(c -> BeanUtil.copyProperties(c, CouponVO.class))
                        .collect(Collectors.toList());
            }
        }

        // 补充用户领取信息（用户数据不缓存，每次查库）
        for (CouponVO vo : result) {
            int claimed = userCouponMapper.countUserClaims(userId, vo.getId());
            vo.setMyClaimedCount(claimed);
            vo.setClaimedByMe(claimed > 0);
        }
        return result;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void claimCoupon(Long userId, Long couponId) {
        Coupon coupon = couponMapper.selectById(couponId);
        if (coupon == null) {
            throw new RuntimeException("优惠券不存在");
        }
        if (coupon.getStatus() != 1) {
            throw new RuntimeException("该优惠券已下架");
        }
        LocalDateTime now = LocalDateTime.now();
        if (now.isBefore(coupon.getStartTime())) {
            throw new RuntimeException("该优惠券尚未开始领取");
        }
        if (now.isAfter(coupon.getEndTime())) {
            throw new RuntimeException("该优惠券已过期");
        }

        //已经领取该优惠卷的数量
        int myClaims = userCouponMapper.countUserClaims(userId, couponId);
        int limit = coupon.getPerUserLimit() != null ? coupon.getPerUserLimit() : 1;
        if (myClaims >= limit) {
            throw new RuntimeException("您已达到领取上限");
        }

        // 原子扣减库存（数据库层面保证 total_stock > 0，防止并发超领）
        int rows = couponMapper.decreaseStock(couponId);
        if (rows <= 0) {
            throw new RuntimeException("该优惠券已被抢光");
        }

        // 延迟双删：先删缓存
        evictAvailableCache();

        // 创建用户优惠券记录
        UserCoupon uc = new UserCoupon();
        uc.setUserId(userId);
        uc.setCouponId(couponId);
        uc.setStatus(0); // 未使用
        uc.setClaimTime(LocalDateTime.now());
        userCouponMapper.insert(uc);

        log.info("[优惠券] 用户 {} 领取了优惠券 {}", userId, couponId);
    }

    @Override
    public List<UserCouponVO> getUserCoupons(Long userId, Integer status) {
        LambdaQueryWrapper<UserCoupon> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(UserCoupon::getUserId, userId);
        if (status != null) {
            wrapper.eq(UserCoupon::getStatus, status);
        }
        wrapper.orderByDesc(UserCoupon::getClaimTime);

        List<UserCoupon> list = userCouponMapper.selectList(wrapper);
        
        // 批量加载关联的优惠券信息，避免 N+1
        List<Long> couponIds = list.stream().map(UserCoupon::getCouponId).distinct().toList();
        Map<Long, Coupon> couponMap = Collections.emptyMap();
        if (!couponIds.isEmpty()) {
            List<Coupon> coupons = couponMapper.selectBatchIds(couponIds);
            couponMap = coupons.stream().collect(Collectors.toMap(Coupon::getId, c -> c));
        }
        
        final Map<Long, Coupon> finalCouponMap = couponMap;
        return list.stream().map(uc -> convertToUserCouponVO(uc, finalCouponMap)).collect(Collectors.toList());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void useCoupon(Long userId, Long userCouponId) {
        UserCoupon uc = userCouponMapper.selectById(userCouponId);
        if (uc == null || !uc.getUserId().equals(userId)) {
            throw new RuntimeException("优惠券不存在");
        }
        if (uc.getStatus() != 0) {
            throw new RuntimeException("该优惠券已使用或已过期");
        }

        // 检查是否过期
        Coupon coupon = couponMapper.selectById(uc.getCouponId());
        if (coupon != null && LocalDateTime.now().isAfter(coupon.getEndTime())) {
            uc.setStatus(2); // 标记为过期
            userCouponMapper.updateById(uc);
            throw new RuntimeException("该优惠券已过期");
        }

        uc.setStatus(1); // 已使用
        uc.setUseTime(LocalDateTime.now());
        userCouponMapper.updateById(uc);

        log.info("[优惠券] 用户 {} 使用了优惠券 {}", userId, userCouponId);
    }

    // ========== 工具方法 ==========


    private UserCouponVO convertToUserCouponVO(UserCoupon uc, Map<Long, Coupon> couponMap) {
        UserCouponVO vo = new UserCouponVO();
        BeanUtils.copyProperties(uc, vo);
        // 从批量预加载的 Map 中获取优惠券信息，避免 N+1
        Coupon coupon = couponMap.get(uc.getCouponId());
        if (coupon != null) {
            vo.setCouponName(coupon.getName());
            vo.setType(coupon.getType());
            vo.setTypeName(getTypeName(coupon.getType()));
            vo.setThresholdAmount(coupon.getThresholdAmount());
            vo.setDiscountAmount(coupon.getDiscountAmount());
            vo.setDiscountRate(coupon.getDiscountRate());
            vo.setMaxDiscount(coupon.getMaxDiscount());
            vo.setStartTime(coupon.getStartTime());
            vo.setEndTime(coupon.getEndTime());
        }
        // 状态名称
        switch (uc.getStatus()) {
            case 0: vo.setStatusName("未使用"); break;
            case 1: vo.setStatusName("已使用"); break;
            case 2: vo.setStatusName("已过期"); break;
            default: vo.setStatusName("未知"); break;
        }
        return vo;
    }

    private String getTypeName(Integer type) {
        if (type == null) return "未知";
        switch (type) {
            case 1: return "满减";
            case 2: return "折扣";
            case 3: return "固定减免";
            default: return "未知";
        }
    }

    /**
     * 延迟双删：立即删除 + 延迟 500ms 再删一次
     */
    private void evictCouponCache(Long id) {
        String key = CouponRedisKey.COUPON_DETAIL + id;
        redisUtil.delete(key);
        redisUtil.deleteAsync(key, 500);
    }

    /**
     * 延迟双删：立即删除 + 延迟 500ms 再删一次
     */
    private void evictAvailableCache() {
        String key = CouponRedisKey.COUPON_AVAILABLE_LIST;
        redisUtil.delete(key);
        redisUtil.deleteAsync(key, 500);
    }
}
