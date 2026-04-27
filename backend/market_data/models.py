from django.db import models


class Brand(models.Model):
    description = models.CharField(max_length=255)

    class Meta:
        db_table = 'brand'


class SubBrand(models.Model):
    description = models.CharField(max_length=255)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, db_column='brand_fk')

    class Meta:
        db_table = 'subbrand'


class Product(models.Model):
    description = models.CharField(max_length=500)
    sub_brand = models.ForeignKey(SubBrand, on_delete=models.CASCADE, db_column='sub_brand_fk')

    class Meta:
        db_table = 'product'


class Market(models.Model):
    description = models.CharField(max_length=255)
    description_2 = models.CharField(max_length=255)

    class Meta:
        db_table = 'market'


class Data(models.Model):
    market = models.ForeignKey(Market, on_delete=models.CASCADE, db_column='market_fk')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='product_fk')
    value = models.IntegerField()
    weighted_distribution = models.IntegerField()
    date = models.DateField()
    period_weeks = models.IntegerField()

    class Meta:
        db_table = 'data'
