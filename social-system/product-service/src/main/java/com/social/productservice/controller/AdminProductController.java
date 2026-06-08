package com.social.productservice.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.social.productservice.domain.dto.ProductQueryDTO;
import com.social.productservice.domain.po.Category;
import com.social.productservice.domain.vo.ProductListVO;
import com.social.productservice.domain.vo.ProductVO;
import com.social.productservice.service.ProductService;
import com.social.socialcommon.result.Result;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/admin/product")
public class AdminProductController {

    @Autowired
    private ProductService productService;

    @GetMapping("/all")
    public Result<IPage<ProductListVO>> getAdminProductList(ProductQueryDTO queryDTO, HttpServletRequest request) {
        try {
            if (!isAdmin(request)) {
                return Result.error("无管理员权限");
            }
            IPage<ProductListVO> page = productService.getProductPage(queryDTO);
            return Result.success("查询成功", page);
        } catch (Exception e) {
            log.error("管理端查询商品列表失败", e);
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/{id}")
    public Result<ProductVO> getAdminProductDetail(@PathVariable Long id, HttpServletRequest request) {
        try {
            if (!isAdmin(request)) {
                return Result.error("无管理员权限");
            }
            ProductVO product = productService.getProductDetail(id);
            return Result.success(product);
        } catch (Exception e) {
            log.error("管理端获取商品详情失败", e);
            return Result.error(e.getMessage());
        }
    }

    @PutMapping("/toggle-status/{id}")
    public Result<Boolean> adminToggleProductStatus(
            @PathVariable Long id,
            @RequestParam Integer status,
            HttpServletRequest request) {
        try {
            if (!isAdmin(request)) {
                return Result.error("无管理员权限");
            }
            if (status != 0 && status != 1) {
                return Result.error("状态值无效，只能为0(下架)或1(上架)");
            }
            boolean updated = productService.toggleProductStatus(id, null, status);
            if (updated) {
                String msg = status == 1 ? "上架成功" : "下架成功";
                return Result.success(msg, true);
            } else {
                return Result.error("操作失败");
            }
        } catch (Exception e) {
            log.error("管理端切换商品状态失败", e);
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/categories")
    public Result<List<Category>> getAllCategories(HttpServletRequest request) {
        try {
            if (!isAdmin(request)) {
                return Result.error("无管理员权限");
            }
            return Result.success(productService.getAllCategories());
        } catch (Exception e) {
            log.error("获取分类列表失败", e);
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/category")
    public Result<Boolean> addCategory(@RequestBody Map<String, Object> body, HttpServletRequest request) {
        try {
            if (!isAdmin(request)) {
                return Result.error("无管理员权限");
            }
            String name = (String) body.get("name");
            Integer sortOrder = body.get("sortOrder") != null ? (Integer) body.get("sortOrder") : 0;
            if (name == null || name.trim().isEmpty()) {
                return Result.error("分类名称不能为空");
            }
            productService.addCategory(name.trim(), sortOrder);
            return Result.success("添加成功", true);
        } catch (Exception e) {
            log.error("添加分类失败", e);
            return Result.error(e.getMessage());
        }
    }

    @PutMapping("/category/{id}")
    public Result<Boolean> updateCategory(@PathVariable Long id, @RequestBody Map<String, Object> body, HttpServletRequest request) {
        try {
            if (!isAdmin(request)) {
                return Result.error("无管理员权限");
            }
            String name = (String) body.get("name");
            Integer sortOrder = body.get("sortOrder") != null ? (Integer) body.get("sortOrder") : null;
            Integer status = body.get("status") != null ? (Integer) body.get("status") : null;
            productService.updateCategory(id, name, sortOrder, status);
            return Result.success("更新成功", true);
        } catch (Exception e) {
            log.error("更新分类失败", e);
            return Result.error(e.getMessage());
        }
    }

    @DeleteMapping("/category/{id}")
    public Result<Boolean> deleteCategory(@PathVariable Long id, HttpServletRequest request) {
        try {
            if (!isAdmin(request)) {
                return Result.error("无管理员权限");
            }
            productService.deleteCategory(id);
            return Result.success("删除成功", true);
        } catch (Exception e) {
            log.error("删除分类失败", e);
            return Result.error(e.getMessage());
        }
    }

    private boolean isAdmin(HttpServletRequest request) {
        String role = request.getHeader("X-User-Role");
        return "ADMIN".equals(role);
    }
}
