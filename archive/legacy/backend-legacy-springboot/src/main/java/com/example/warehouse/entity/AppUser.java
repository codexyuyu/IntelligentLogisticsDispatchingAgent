package com.example.warehouse.entity;

import java.time.LocalDateTime;

public class AppUser {
    private Long id;
    private String username;
    private String passwordHash;
    /**
     * 用户权限：0=仓库主管，1=仓库管理员，2=游客。
     */
    private Integer userPermission;
    private LocalDateTime userRegistrationTime;
    private LocalDateTime userPermissionModifiedTime;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }
    public String getPasswordHash() { return passwordHash; }
    public void setPasswordHash(String passwordHash) { this.passwordHash = passwordHash; }
    public Integer getUserPermission() { return userPermission; }
    public void setUserPermission(Integer userPermission) { this.userPermission = userPermission; }
    public LocalDateTime getUserRegistrationTime() { return userRegistrationTime; }
    public void setUserRegistrationTime(LocalDateTime userRegistrationTime) { this.userRegistrationTime = userRegistrationTime; }
    public LocalDateTime getUserPermissionModifiedTime() { return userPermissionModifiedTime; }
    public void setUserPermissionModifiedTime(LocalDateTime userPermissionModifiedTime) { this.userPermissionModifiedTime = userPermissionModifiedTime; }

    /**
     * 兼容前端显示：数据库不再保存 display_name，显示名称由权限自动生成。
     */
    public String getDisplayName() {
        if (userPermission != null && userPermission == 0) return "仓库主管";
        if (userPermission != null && userPermission == 1) return "仓库管理员";
        if (userPermission != null && userPermission == 2) return "游客";
        return username;
    }

    /**
     * 兼容前端显示：保留 role 字段，但值改为中文权限名。
     */
    public String getRole() {
        if (userPermission != null && userPermission == 0) return "仓库主管";
        if (userPermission != null && userPermission == 1) return "仓库管理员";
        if (userPermission != null && userPermission == 2) return "游客";
        return "未知权限";
    }

    public String getStatus() { return "ACTIVE"; }

    /**
     * 兼容旧前端 createdAt 字段，同时新增 userRegistrationTime 字段。
     */
    public LocalDateTime getCreatedAt() { return userRegistrationTime; }
}
