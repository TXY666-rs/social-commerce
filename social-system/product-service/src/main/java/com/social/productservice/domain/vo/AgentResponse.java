package com.social.productservice.domain.vo;

import lombok.Data;

import java.util.List;

@Data
public class AgentResponse {

    private List<ToAgentProductVO> agentProductVOList;

    private Integer total;
}
