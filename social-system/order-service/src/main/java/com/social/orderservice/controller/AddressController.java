package com.social.orderservice.controller;

import com.social.orderservice.domain.po.Address;
import com.social.orderservice.service.AddressService;
import com.social.socialcommon.result.Result;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Slf4j
@RestController
@RequestMapping("/address")
public class AddressController {

    @Autowired
    private AddressService addressService;

    @GetMapping("/list")
    public Result<List<Address>> getUserAddresses(HttpServletRequest request) {
        try {
            Long userId = getUserIdFromRequest(request);
            return Result.success(addressService.getUserAddresses(userId));
        } catch (Exception e) {
            log.error("查询地址列表失败", e);
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/{id}")
    public Result<Address> getAddress(@PathVariable Long id) {
        try {
            return Result.success(addressService.getAddress(id));
        } catch (Exception e) {
            log.error("查询地址详情失败", e);
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/create")
    public Result<Address> createAddress(@RequestBody Address address, HttpServletRequest request) {
        try {
            Long userId = getUserIdFromRequest(request);
            Address created = addressService.createAddress(userId, address);
            return Result.success("地址创建成功", created);
        } catch (Exception e) {
            log.error("创建地址失败", e);
            return Result.error(e.getMessage());
        }
    }

    @PutMapping("/{id}")
    public Result<Boolean> updateAddress(@PathVariable Long id, @RequestBody Address address, HttpServletRequest request) {
        try {
            Long userId = getUserIdFromRequest(request);
            boolean updated = addressService.updateAddress(id, userId, address);
            return updated ? Result.success("更新成功", true) : Result.error("更新失败");
        } catch (Exception e) {
            log.error("更新地址失败", e);
            return Result.error(e.getMessage());
        }
    }

    @DeleteMapping("/{id}")
    public Result<Boolean> deleteAddress(@PathVariable Long id, HttpServletRequest request) {
        try {
            Long userId = getUserIdFromRequest(request);
            boolean deleted = addressService.deleteAddress(id, userId);
            return deleted ? Result.success("删除成功", true) : Result.error("删除失败");
        } catch (Exception e) {
            log.error("删除地址失败", e);
            return Result.error(e.getMessage());
        }
    }

    @PutMapping("/default/{id}")
    public Result<Boolean> setDefault(@PathVariable Long id, HttpServletRequest request) {
        try {
            Long userId = getUserIdFromRequest(request);
            boolean set = addressService.setDefault(id, userId);
            return set ? Result.success("设置成功", true) : Result.error("设置失败");
        } catch (Exception e) {
            log.error("设置默认地址失败", e);
            return Result.error(e.getMessage());
        }
    }

    private Long getUserIdFromRequest(HttpServletRequest request) {
        String userIdStr = request.getHeader("X-User-Id");
        if (userIdStr == null || userIdStr.isEmpty()) {
            throw new RuntimeException("未提供有效令牌");
        }
        return Long.valueOf(userIdStr);
    }
}
