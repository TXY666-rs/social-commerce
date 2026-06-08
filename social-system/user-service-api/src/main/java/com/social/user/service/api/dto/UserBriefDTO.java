package com.social.user.service.api.dto;


import lombok.Data;

@Data
public class UserBriefDTO {

    private Long id;

    private String nickname;

    private String avatar;

    private String username;
}
