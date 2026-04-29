I want a bar chart with years at the X-axis and accumulated value on Y-axis.

This chart will live in a new section of the frontend called "evolution"

The user will have a selector on top of the chart to choose between "Brand", "Product", "Market". Then, a second selector will allow the user to select the specific value for the previosly selected category. e.g: The user selects Market first and then the second selector allows to select "Market 1", "Market 2", etc. All based on the values for that property. The chart will aggregate Data based on the user selection. 

DB rows with null or empty values for the selected category from first selector will be ignored