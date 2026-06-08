package com.social.productservice.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.social.productservice.domain.po.Category;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface CategoryMapper extends BaseMapper<Category> {
}
