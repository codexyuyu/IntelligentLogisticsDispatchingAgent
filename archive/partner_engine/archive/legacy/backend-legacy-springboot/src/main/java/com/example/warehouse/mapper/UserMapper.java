package com.example.warehouse.mapper;

import com.example.warehouse.entity.AppUser;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

@Mapper
public interface UserMapper {
    String USER_COLUMNS = "id, username, password as passwordHash, " +
            "case when role = 'ADMIN' then 0 else 1 end as userPermission, " +
            "create_time as userRegistrationTime, null as userPermissionModifiedTime";

    @Select("select " + USER_COLUMNS + " from app_user where username = #{username} limit 1")
    AppUser findByUsername(String username);

    @Select("select " + USER_COLUMNS + " from app_user where id = #{id} limit 1")
    AppUser findById(Long id);

    @Select("select count(*) from app_user where username = #{username}")
    int countByUsername(String username);

    @Insert("insert into app_user(username, password, display_name, role, create_time) values(#{username}, #{passwordHash}, #{username}, 'USER', now())")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(AppUser user);

    @Update("update app_user set role = case #{userPermission} when 0 then 'ADMIN' else 'USER' end where id = #{userId}")
    int updatePermission(@Param("userId") Long userId, @Param("userPermission") Integer userPermission);
}
