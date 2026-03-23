// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IProductPrice {
    function productPrice(uint256 slicerId, uint256 productId, address currency, uint256 quantity, address buyer, bytes calldata data) external view returns (uint256 ethPrice, uint256 currencyPrice);
}

interface IProductAction {
    function onProductPurchase(uint256 slicerId, uint256 productId, address buyer, uint256 quantity, bytes calldata slicerCustomData, bytes calldata buyerCustomData) external;
}

contract OpusGodPricingHook is IProductPrice, IProductAction {
    address public owner;
    uint256 public basePriceWei;
    uint256 public demandMultiplier;

    event PurchaseProcessed(address buyer, uint256 productId, uint256 quantity);
    event PriceUpdated(uint256 newBasePriceWei, uint256 newDemandMultiplier);

    constructor(uint256 _basePriceWei) {
        owner = msg.sender;
        basePriceWei = _basePriceWei;
        demandMultiplier = 10000;
    }

    modifier onlyOwner() { require(msg.sender == owner, "Not owner"); _; }

    function productPrice(uint256, uint256, address, uint256 quantity, address, bytes calldata) external view override returns (uint256 ethPrice, uint256 currencyPrice) {
        ethPrice = (basePriceWei * quantity * demandMultiplier) / 10000;
        currencyPrice = 0;
    }

    function onProductPurchase(uint256, uint256 productId, address buyer, uint256 quantity, bytes calldata, bytes calldata) external override {
        emit PurchaseProcessed(buyer, productId, quantity);
    }

    function updatePricing(uint256 _basePriceWei, uint256 _demandMultiplier) external onlyOwner {
        basePriceWei = _basePriceWei;
        demandMultiplier = _demandMultiplier;
        emit PriceUpdated(_basePriceWei, _demandMultiplier);
    }
}
