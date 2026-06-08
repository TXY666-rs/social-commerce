-- auto-generated definition
create table product
(
    id            bigint not null
        constraint id
        primary key,
    name          varchar(100),
    description   text,
    price         numeric(10, 2),
    stock         integer,
    category      varchar(50),
    image         varchar(255),
    seller_id     bigint,
    status        smallint,
    view_count    integer,
    is_deleted    smallint,
    create_time   timestamp,
    update_time   timestamp,
    delivery_type varchar(50)
);

alter table product
    owner to postgres;



-- auto-generated definition
create table category
(
    id          bigint,
    name        varchar(50),
    sort_order  integer,
    status      smallint,
    create_time timestamp,
    update_time timestamp,
    is_deleted  smallint
);

alter table category
    owner to postgres;



-- auto-generated definition
create table product_size
(
    id          bigint,
    product_id  bigint,
    size_name   varchar(30),
    size_price  numeric(10, 2),
    size_stock  integer,
    status      smallint,
    is_deleted  smallint,
    create_time timestamp,
    update_time timestamp
);

alter table product_size
    owner to postgres;


