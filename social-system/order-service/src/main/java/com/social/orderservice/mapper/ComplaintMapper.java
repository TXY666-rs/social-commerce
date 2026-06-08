package com.social.orderservice.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.social.orderservice.domain.po.Complaint;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface ComplaintMapper extends BaseMapper<Complaint> {
}
