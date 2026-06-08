package com.social.user.service.api.feign;

import com.social.socialcommon.result.Result;
import com.social.user.service.api.dto.UserBriefDTO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.openfeign.FallbackFactory;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class UserClientFallbackFactory implements FallbackFactory<UserClient> {

    @Override
    public UserClient create(Throwable cause) {
        log.error("UserClient 调用失败，启用 fallback", cause);
        return new UserClient() {
            @Override
            public Result<UserBriefDTO> getUserBrief(Long id) {
                return Result.error("用户服务暂不可用");
            }

            @Override
            public Result<Map<Long, UserBriefDTO>> batchGetUserBrief(List<Long> ids) {
                return Result.success(new HashMap<>());
            }

            @Override
            public Result<Map<String, Object>> getAdminUserPage(String keyword, Integer status, Integer role, Integer pageNum, Integer pageSize) {
                return Result.error("用户服务暂不可用");
            }

            @Override
            public Result<Map<String, Object>> getAdminUserDetail(Long id) {
                return Result.error("用户服务暂不可用");
            }

            @Override
            public Result<Boolean> adminToggleUserStatus(Long id, Integer status) {
                return Result.error("用户服务暂不可用");
            }

            @Override
            public Result<Boolean> adminResetPassword(Long id, String newPassword) {
                return Result.error("用户服务暂不可用");
            }

            @Override
            public Result<Long> getAdminUserCount() {
                return Result.error("用户服务暂不可用");
            }
        };
    }
}
