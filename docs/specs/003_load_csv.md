I have a CSV with the following header

M Desc,VAL,WTD,Product,LEVEL,CATEGORY,MANUFACTURER,BRAND,SUBBRAND,SEGMENT,PACKSIZE,SIZE,FORMAT,TIME,M Desc 2,DATETIME

The csv represents some retails sales data being each column:

* M Desc: The market description, which consistently identifies the region or market segment being analyzed (e.g., "MARKET3").
* VAL: The numerical sales value for the given product and time period.
* WTD: Likely stands for "Weighted Distribution," representing the percentage or reach of the product in the specified market. It is a percentage but the value is multiplied by 100. e.g: In the file we have 9400 which stands for 94%
* Product: A detailed text description of the specific item, often including the brand, type, and weight (e.g., "CHS ORGANIC TREE UT PLUS UT VETO BRETS FAMILY 400").
* LEVEL: Specifies the hierarchy level of the data, which is consistently "ITEM" in this dataset.
* CATEGORY: The broad product category (e.g., "CHS" for cheese).
* MANUFACTURER: The company responsible for producing the item (e.g., "ORGANIC TREE", "SUPER FOOD", "PRIVATE LABEL").
* BRAND: The primary brand name under which the product is sold (e.g., "UT PLUS", "SON WIIT-PEX").
* SUBBRAND: A secondary brand classification for more specific product lines (e.g., "UT VETO BRETS", "CAYNTGAWN").
* SEGMENT: The target consumer group for the product (e.g., "FAMILY", "ADULT", "KIDS").
* PACKSIZE: The range or bracket of the product's weight (e.g., "400-499G").
* SIZE: The specific numerical weight or volume of the product (e.g., "400.0").
* FORMAT: The physical form or texture of the product (e.g., "CHUNKY", "SHREDDED/GRATED").
* TIME: A descriptive time period code representing a specific month, number of weeks, and an end date (e.g., "AUG16 4WKS 04/09/16").
* M Desc 2: A secondary market or retailer description (e.g., "TOT RETAILER 1").
* DATETIME: The specific end date of the reporting period in a standard YYYY-MM-DD format (e.g., "2016-09-04").

I want a django command that loads into the database a csv file passed as an argument. The argument is the csv file name and it will be stored in the folder docs/data.

The command should live in the django app "market_data"

The mapping for the CSV file into the models will be:

* Brand
    - description: BRAND

* SubBrand
    - description: SUBBRAND
    - brand_fk: Brand PK that matches BRAND column
* Product
    - description: Product
    - sub_brand_fk: SubBrand PK that matches SUBBRAND column
* Market
    - description: M Desc
    - description_2: M Desc 2
* Data
    - market_fk: Market PK that matches M Desc and M Desc 2 columns
    - product_fk: Product PK that matches the Product column
    - value: VAL
    - date: DATETIME
    - period_weeks: Selection group from regExp /(\d)WKS/ run on column TIME