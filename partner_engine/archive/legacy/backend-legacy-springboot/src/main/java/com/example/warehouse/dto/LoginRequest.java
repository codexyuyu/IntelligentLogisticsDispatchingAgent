package com.example.warehouse.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

public class LoginRequest {
    @NotBlank(message = "用户名不能为空")
    @Pattern(regexp = "^[A-Za-z!@#$%^&*._\\-+=]+$", message = "用户名只能使用英文字母和常见特殊字符，不能包含数字、中文或空格")
    private String username;

    @NotBlank(message = "密码不能为空")
    @Pattern(regexp = "^(?!\\s)(?!.*\\s$)(?!.*[\\u4e00-\\u9fa5]).*$", message = "密码首尾不能为空格，且禁止包含中文")
    private String password;

    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }
    public String getPassword() { return password; }
    public void setPassword(String password) { this.password = password; }
}
