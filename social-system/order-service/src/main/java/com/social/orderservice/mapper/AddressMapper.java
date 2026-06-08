package com.social.orderservice.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.social.orderservice.domain.po.Address;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface AddressMapper extends BaseMapper<Address> {
}
