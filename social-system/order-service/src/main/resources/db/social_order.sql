-- auto-generated definition
create table "order"
(
    id               varchar(20) not null
        constraint id
            primary key,
    user_id          bigint,
    product_id       bigint,
    quantity         integer,
    total_price      numeric(10, 2),
    status           smallint,
    receiver_name    varchar(50),
    receiver_phone   varchar(20),
    receiver_address varchar(255),
    pay_time         timestamp,
    delivery_time    timestamp,
    complete_time    timestamp,
    remark           varchar(255),
    is_deleted       smallint,
    create_time      timestamp,
    update_time      timestamp,
    seller_id        bigint,
    original_price   numeric(10, 2),
    discount_amount  numeric(10, 2),
    user_coupon_id   bigint,
    tracking_number  varchar(100),
    delivery_remark  varchar(500)
);

alter table "order"
    owner to postgres;

create index user_id_idx
    on "order" (user_id);

comment on index user_id_idx is '用户id索引';

