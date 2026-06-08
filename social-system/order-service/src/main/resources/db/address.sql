-- 地址簿表
create table address
(
    id              bigint not null
    constraint address_pk primary key,
    user_id         bigint not null,
    receiver_name   varchar(50),
    receiver_phone  varchar(20),
    province        varchar(50),
    city            varchar(50),
    district        varchar(50),
    detail_address  varchar(255),
    is_default      smallint default 0,
    is_deleted      smallint default 0,
    create_time     timestamp,
    update_time     timestamp
);

alter table address owner to postgres;

create index address_user_id_idx on address (user_id);
comment on index address_user_id_idx is '用户id索引';

-- 插入测试数据（user_id = 1 的测试地址）
insert into address (id, user_id, receiver_name, receiver_phone, province, city, district, detail_address, is_default, is_deleted, create_time, update_time)
values
    (1, 1, '张三', '13800138000', '广东省', '深圳市', '南山区', '科技园南路腾讯大厦1楼', 1, 0, now(), now()),
    (2, 1, '李四', '13900139000', '北京市', '朝阳区', '望京街道', '望京SOHO T3 12层', 0, 0, now(), now()),
    (3, 1, '王五', '13700137000', '上海市', '浦东新区', '陆家嘴街道', '东方明珠塔附近花园石桥路100号', 0, 0, now(), now());
