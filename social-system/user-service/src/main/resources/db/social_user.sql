-- auto-generated definition
create table "user"
(
    id              bigint,
    username        varchar(50),
    nickname        varchar(50),
    password        varchar(100),
    email           varchar(100),
    phone           varchar(20),
    avatar          varchar(255),
    gender          smallint,
    birthday        date,
    signature       varchar(255),
    status          smallint,
    last_login_time timestamp,
    last_login_ip   varchar(50),
    is_deleted      smallint,
    create_time     timestamp,
    update_time     timestamp,
    online_status   smallint,
    role            smallint
);

alter table "user"
    owner to postgres;

