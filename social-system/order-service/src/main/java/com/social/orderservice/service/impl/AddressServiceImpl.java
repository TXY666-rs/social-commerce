package com.social.orderservice.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.social.orderservice.domain.po.Address;
import com.social.orderservice.mapper.AddressMapper;
import com.social.orderservice.service.AddressService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@Service
public class AddressServiceImpl implements AddressService {

    @Autowired
    private AddressMapper addressMapper;

    @Override
    public List<Address> getUserAddresses(Long userId) {
        return addressMapper.selectList(
                new LambdaQueryWrapper<Address>()
                        .eq(Address::getUserId, userId)
                        .orderByDesc(Address::getIsDefault)
                        .orderByDesc(Address::getUpdateTime)
        );
    }

    @Override
    public Address getAddress(Long id) {
        Address address = addressMapper.selectById(id);
        if (address == null) {
            throw new RuntimeException("地址不存在");
        }
        return address;
    }

    @Override
    @Transactional
    public Address createAddress(Long userId, Address address) {
        address.setUserId(userId);
        address.setIsDeleted(0);
        address.setCreateTime(LocalDateTime.now());
        address.setUpdateTime(LocalDateTime.now());

        // 如果设为默认地址，先取消其他默认
        if (address.getIsDefault() != null && address.getIsDefault() == 1) {
            clearDefaultAddress(userId);
        }

        // 如果是第一个地址，自动设为默认
        long count = addressMapper.selectCount(
                new LambdaQueryWrapper<Address>().eq(Address::getUserId, userId));
        if (count == 0) {
            address.setIsDefault(1);
        }

        addressMapper.insert(address);
        log.info("地址创建成功, id={}, userId={}", address.getId(), userId);
        return address;
    }

    @Override
    @Transactional
    public boolean updateAddress(Long id, Long userId, Address address) {
        Address existing = getAddress(id);
        if (!existing.getUserId().equals(userId)) {
            throw new RuntimeException("无权修改该地址");
        }

        address.setId(id);
        address.setUserId(userId);
        address.setUpdateTime(LocalDateTime.now());

        if (address.getIsDefault() != null && address.getIsDefault() == 1) {
            clearDefaultAddress(userId);
        }

        return addressMapper.updateById(address) > 0;
    }

    @Override
    public boolean deleteAddress(Long id, Long userId) {
        Address existing = getAddress(id);
        if (!existing.getUserId().equals(userId)) {
            throw new RuntimeException("无权删除该地址");
        }
        return addressMapper.deleteById(id) > 0;
    }

    @Override
    @Transactional
    public boolean setDefault(Long id, Long userId) {
        Address existing = getAddress(id);
        if (!existing.getUserId().equals(userId)) {
            throw new RuntimeException("无权操作该地址");
        }

        clearDefaultAddress(userId);

        Address update = new Address();
        update.setId(id);
        update.setIsDefault(1);
        update.setUpdateTime(LocalDateTime.now());
        return addressMapper.updateById(update) > 0;
    }

    private void clearDefaultAddress(Long userId) {
        addressMapper.update(null,
                new LambdaUpdateWrapper<Address>()
                        .eq(Address::getUserId, userId)
                        .eq(Address::getIsDefault, 1)
                        .set(Address::getIsDefault, 0));
    }
}
