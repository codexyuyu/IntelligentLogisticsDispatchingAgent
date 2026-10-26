package com.example.warehouse.service;

import com.example.warehouse.dto.LoginRequest;
import com.example.warehouse.dto.RegisterRequest;
import com.example.warehouse.entity.AppUser;
import com.example.warehouse.mapper.UserMapper;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import java.util.regex.Pattern;

@Service
public class AuthService {
    /**
     * 仅用于兼容早期演示数据中的 SHA-256 密码。新注册用户全部使用 BCrypt。
     */
    private static final String LEGACY_PASSWORD_SALT = "smart-warehouse-demo-v1";
    private static final Pattern USERNAME_PATTERN = Pattern.compile("^[A-Za-z0-9!@#$%^&*._\\-+=]+$");
    private static final Pattern CHINESE_PATTERN = Pattern.compile("[\\u4e00-\\u9fa5]");

    private final UserMapper userMapper;
    private final PasswordEncoder passwordEncoder;

    public AuthService(UserMapper userMapper, PasswordEncoder passwordEncoder) {
        this.userMapper = userMapper;
        this.passwordEncoder = passwordEncoder;
    }

    public Map<String, Object> register(RegisterRequest request) {
        String username = normalizeUsername(request.getUsername());
        validatePassword(request.getPassword());
        if (userMapper.countByUsername(username) > 0) {
            throw new IllegalStateException("用户名已存在，请换一个用户名");
        }

        AppUser user = new AppUser();
        user.setUsername(username);
        user.setPasswordHash(passwordEncoder.encode(request.getPassword()));
        user.setUserPermission(1);
        user.setUserRegistrationTime(LocalDateTime.now());
        user.setUserPermissionModifiedTime(null);
        userMapper.insert(user);
        return buildAuthPayload(user);
    }

    public Map<String, Object> login(LoginRequest request) {
        String username = normalizeUsername(request.getUsername());
        validatePassword(request.getPassword());
        AppUser user = userMapper.findByUsername(username);
        if (user == null || !matchesPassword(request.getPassword(), user.getPasswordHash())) {
            throw new IllegalArgumentException("用户名或密码错误");
        }
        return buildAuthPayload(user);
    }

    private Map<String, Object> buildAuthPayload(AppUser user) {
        Map<String, Object> safeUser = new LinkedHashMap<>();
        safeUser.put("id", user.getId());
        safeUser.put("username", user.getUsername());
        safeUser.put("displayName", user.getDisplayName());
        safeUser.put("role", user.getRole());
        safeUser.put("roleCode", user.getUserPermission());
        safeUser.put("userPermission", user.getUserPermission());
        safeUser.put("status", user.getStatus());
        safeUser.put("createdAt", user.getCreatedAt());
        safeUser.put("userRegistrationTime", user.getUserRegistrationTime());
        safeUser.put("userPermissionModifiedTime", user.getUserPermissionModifiedTime());

        String tokenPayload = user.getId() + ":" + user.getUsername() + ":" + System.currentTimeMillis() + ":" + UUID.randomUUID();
        String token = Base64.getUrlEncoder().withoutPadding().encodeToString(tokenPayload.getBytes(StandardCharsets.UTF_8));
        return Map.of("token", token, "user", safeUser);
    }

    private boolean matchesPassword(String rawPassword, String storedPasswordHash) {
        if (!StringUtils.hasText(storedPasswordHash)) {
            return false;
        }
        if (storedPasswordHash.startsWith("$2a$") || storedPasswordHash.startsWith("$2b$") || storedPasswordHash.startsWith("$2y$")) {
            return passwordEncoder.matches(rawPassword, storedPasswordHash);
        }
        if (rawPassword.equals(storedPasswordHash)) {
            return true;
        }
        return legacySha256(rawPassword).equals(storedPasswordHash);
    }

    private String normalizeUsername(String username) {
        if (!StringUtils.hasText(username)) {
            throw new IllegalArgumentException("用户名不能为空");
        }
        String normalized = username.trim().toLowerCase();
        if (!USERNAME_PATTERN.matcher(normalized).matches()) {
            throw new IllegalArgumentException("用户名只能使用英文字母、数字和常见特殊字符，不能包含中文或空格");
        }
        return normalized;
    }

    private void validatePassword(String password) {
        if (!StringUtils.hasText(password)) {
            throw new IllegalArgumentException("密码不能为空");
        }
        if (!password.equals(password.strip())) {
            throw new IllegalArgumentException("密码首尾不能为空格");
        }
        if (CHINESE_PATTERN.matcher(password).find()) {
            throw new IllegalArgumentException("密码禁止包含中文");
        }
    }

    private String legacySha256(String rawPassword) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] encoded = digest.digest((LEGACY_PASSWORD_SALT + ":" + rawPassword).getBytes(StandardCharsets.UTF_8));
            return Base64.getEncoder().encodeToString(encoded);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("密码校验失败", e);
        }
    }
}
