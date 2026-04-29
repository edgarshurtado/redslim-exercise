from django.db import models


class Brand(models.Model):
    description = models.CharField(max_length=255)

    class Meta:
        db_table = 'brand'
        constraints = [
            models.UniqueConstraint(
                fields=['description'],
                name='uniq_brand_description',
            ),
        ]


class SubBrand(models.Model):
    description = models.CharField(max_length=255)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, db_column='brand_fk')

    class Meta:
        db_table = 'subbrand'
        constraints = [
            models.UniqueConstraint(
                fields=['description', 'brand'],
                name='uniq_subbrand_description_brand',
            ),
        ]


class Product(models.Model):
    description = models.CharField(max_length=500)
    sub_brand = models.ForeignKey(SubBrand, on_delete=models.CASCADE, db_column='sub_brand_fk')

    class Meta:
        db_table = 'product'
        constraints = [
            models.UniqueConstraint(
                fields=['description', 'sub_brand'],
                name='uniq_product_description_subbrand',
            ),
        ]


class Market(models.Model):
    description = models.CharField(max_length=255)
    description_2 = models.CharField(max_length=255)

    class Meta:
        db_table = 'market'
        constraints = [
            models.UniqueConstraint(
                fields=['description', 'description_2'],
                name='uniq_market_descriptions',
            ),
        ]


class Data(models.Model):
    market = models.ForeignKey(Market, on_delete=models.CASCADE, db_column='market_fk')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='product_fk')
    value = models.DecimalField(max_digits=12, decimal_places=2)
    weighted_distribution = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    date = models.DateField()
    period_weeks = models.IntegerField()

    class Meta:
        db_table = 'sales_data'
        constraints = [
            models.UniqueConstraint(
                fields=['market', 'product', 'date'],
                name='uniq_data_market_product_date',
            ),
        ]
