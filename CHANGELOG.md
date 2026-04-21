# Changelog

## [2.1.6] - 2026-04-20

### Fixed

#### Critical Bug Fix: ProductTools.search_products

- **`tools/product.py`**: Fixed `search_products` request body structure
  - Was sending all parameters directly in `filter` object
  - API requires `option.BranchInfoCode` (mandatory field)
  - When using `priceCodeList`, must also set `filter.hasPrice = true`
  - When using `priceCodeList`, must populate `filter.priceCodeList` and `filter.branchPriceCodeList`
  - Previous implementation returned HTTP 400 errors
  - Now correctly structures request with both `option` and `filter` objects
  - Validated with manual testing: successfully retrieves products from production API

**Impact**: `totvs_search_products` tool is now fully functional

### Changed

- Updated `.gitignore` to exclude test files (test_manual.py, test_phase2.py, TEST_RESULTS.md, TESTING_ROADMAP.md)

## [2.1.5] - 2026-04-18

### Added - 15 New Endpoints

#### Sales Order - Complete Item Management (10 endpoints)

- **`totvs_add_order_items`**: Add items to existing order (POST `/sales-order/v2/items`)
- **`totvs_remove_order_item`**: Remove item from order (DELETE `/sales-order/v2/items`)
- **`totvs_cancel_order_items`**: Cancel item quantities (POST `/sales-order/v2/cancel-items`)
- **`totvs_change_order_item_quantity`**: Change item quantities (POST `/sales-order/v2/quantity-items`)
- **`totvs_update_order_items_additional`**: Update item additional data (POST `/sales-order/v2/additional-items`)
- **`totvs_add_order_observation`**: Add observation to order (POST `/sales-order/v2/observations-order`)
- **`totvs_update_order_shipping`**: Update shipping/freight data (POST `/sales-order/v2/shipping-order`)
- **`totvs_update_order_additional`**: Update tracking, ecommerce, omni data (POST `/sales-order/v2/additional-order`)
- **`totvs_search_batch_items`**: Search order batches by status and change date (GET `/sales-order/v2/batch-items`)
- **`totvs_create_order_relationship_counts`**: Link counts to order (POST `/sales-order/v2/relationship-counts`)

Sales Order module upgraded from "consultation only" to **full operational management** - add/remove items, adjust quantities, update observations, freight, and tracking via natural language.

#### Product - Missing Write Operations (3 endpoints)

- **`totvs_create_reference`**: Create new product reference (POST `/product/v2/references`)
- **`totvs_update_barcode`**: Update existing barcode (POST `/product/v2/barcodes/update`)
- **`totvs_create_classification_type`**: Create classification type (POST `/product/v2/classifications`)

#### Accounts Receivable - Module Completed (2 endpoints)

- **`totvs_move_gift_check`**: Move gift check (POST `/accounts-receivable/v2/gift-check-movements`)
- **`totvs_upsert_invoice_commission`**: Create/update invoice commission (POST `/accounts-receivable/v2/comission`)

**Accounts Receivable module now covers 100% of official swagger endpoints.**

### Testing

- Added 21 new contract tests covering all 15 new endpoints
- Validates HTTP method, URL, required fields, and body shape
- Total test suite: **57 tests passing** (16 client + 20 regression + 21 new)
- Test execution time: ~0.5s

### Project Stats

- **75+ tools** across 18 modules
- **Accounts Receivable**: 100% swagger coverage
- **Account Payable**: 100% swagger coverage
- **Sales Order**: Full operational management capabilities

## [2.2.0] - 2026-04-18

### Added

#### Testing Infrastructure

- **Automated Testing Suite**: Added 36 comprehensive tests
  - `tests/test_totvs_client.py`: 16 tests covering HTTP client, OAuth2, retry logic, and error handling
  - `tests/test_tools_regressions.py`: 20 regression tests ensuring all 5 critical bug fixes remain fixed
  - `tests/conftest.py`: Shared pytest fixtures with respx mocking
  - `pytest.ini`: pytest configuration with async support

- **Continuous Integration**: GitHub Actions workflow
  - `.github/workflows/tests.yml`: Automated tests on Python 3.11 and 3.12
  - Runs on every push and pull request
  - Completes in under 1 minute

- **Contributing Guide**: `CONTRIBUTING.md`
  - Guidelines for opening pull requests
  - Instructions for running tests locally
  - Code style and quality requirements

### Testing Coverage

- ✅ OAuth2 token acquisition and auto-refresh
- ✅ HTTP retry logic with exponential backoff
- ✅ Error handling and parsing
- ✅ All 5 critical bug fixes from v2.0.1:
  - `update_product_data` uses PUT (not POST)
  - IMAGE endpoints use correct swagger paths
  - `search_voucher` uses GET (not POST)
  - `change_order_status` uses correct payload
  - `change_charge_type` validation works

## [2.0.1] - 2026-04-18

### Fixed

#### Critical Bug Fixes

- **`tools/product.py`**: Fixed `update_product_data` HTTP method from POST to PUT
  - Was returning HTTP 405 (Method Not Allowed) in production
  - Swagger specifies PUT `/api/totvsmoda/product/v2/data`

- **`tools/image.py`**: Complete rewrite with correct swagger endpoints
  - Previous code used `/product-images` which doesn't exist
  - All 3 image tools were returning HTTP 404
  - Now implements 6 correct methods:
    - `search_product_images` - POST `/product/search`
    - `upload_product_image` - POST `/product`
    - `import_image_no_link` - POST `/V2/imports`
    - `upload_person_image` - POST `/persons`
    - `list_person_images` - GET `/persons`
    - `get_person_image_base64` - GET `/person-images`

- **`tools/voucher.py`**: Fixed `search_voucher` HTTP method
  - Changed from POST with body to GET with query params
  - Was returning HTTP 404
  - Removed orphan `get_voucher` method (endpoint doesn't exist in swagger)

- **`tools/sales_order.py`**: Fixed `change_order_status` payload schema
  - Changed field from `newStatus` to `statusOrder`
  - Now enforces valid enum values:
    - `InProgress`, `BillingReleased`, `Blocked`, `InComposition`, `InAnalysis`
  - Was being rejected with HTTP 400 Bad Request
  - Added backward compatibility for `newStatus`
  - Added optional fields: `reasonBlockingCode`, `reasonBlockingDescription`

- **`tools/sales_order.py`**: Enhanced `cancel_order`
  - Added optional `ReasonCancellationDescription` field (max 80 chars)

- **`tools/accounts_receivable.py`**: Fixed `change_charge_type` validation
  - Added validation to ensure `customerCode` OR `customerCpfCnpj` is provided
  - Both fields marked as required in swagger but are mutually exclusive

#### Server Improvements

- **`server.py`**: Fixed ROUTING type hints
  - Removed `"totvs_get_context": None` breaking `dict[str, tuple[str, str]]`
  - Removed orphan `"totvs_get_price_tables_headers"` entry
  - Updated all 6 IMAGE tool mappings to new method names

### Added

- **`server.py`**: Added missing `totvs_search_seller_pending_conditionals` tool
  - Method existed in `tools/analytics.py` but was orphan
  - Now properly registered in TOOLS and ROUTING

## [2.0.0] - 2026-04-16

- Initial release with 16 modules and 135+ tools
