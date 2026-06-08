package com.social.socialgateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

@EnableDiscoveryClient
@SpringBootApplication
public class SocialGatewayApplication {

    public static void main(String[] args) {
        SpringApplication.run(SocialGatewayApplication.class, args);
    }

}
