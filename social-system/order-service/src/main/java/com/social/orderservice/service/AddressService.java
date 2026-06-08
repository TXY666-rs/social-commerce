package com.social.orderservice.service;

import com.social.orderservice.domain.po.Address;

import java.util.List;

public interface AddressService {

    List<Address> getUserAddresses(Long userId);

    Address getAddress(Long id);

    Address createAddress(Long userId, Address address);

    boolean updateAddress(Long id, Long userId, Address address);

    boolean deleteAddress(Long id, Long userId);

    boolean setDefault(Long id, Long userId);
}
