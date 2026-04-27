I want a DB modeled to hold the following information

* Market
    - description: String
    - description_2: String

* Product
    - description: String
    - sub_brand_pk

* Brand
    - description: String

* SubBrand
    - description: String
    - brand_pk

* Data
    - market_fk
    - product_fk
    - value: int
    - weighted_distribution: int
    - date: date
    - period_weeks: int