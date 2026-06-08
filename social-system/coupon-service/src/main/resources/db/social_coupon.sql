-- auto-generated definition
create table coupon
(
    id               bigint,
    name             varchar(100),
    type             smallint,
    threshold_amount numeric(10, 2),
    discount_amount  numeric(10, 2),
    discount_rate    numeric(4, 2),
    max_discount     numeric(10, 2),
    total_stock      integer,
    per_user_limit   integer,
    start_time       timestamp,
    end_time         timestamp,
    status           smallint,
    description      varchar(500),
    create_time      timestamp,
    update_time      timestamp
);

alter table coupon
    owner to postgres;




-- auto-generated definition
create table user_coupon
(
    id         bigint,
    user_id    bigint,
    coupon_id  bigint,
    status     smallint,
    claim_time timestamp,
    use_time   timestamp
);

alter table user_coupon
    owner to postgres;

