from django.contrib.auth.models import User
from django.db import models
from django.db.models import Max, Min, Sum, Avg
from django.utils import timezone
from datetime import datetime, date

from capsulae2.commons import get_random_str
from account.models import Company


class Client(models.Model):
    code = models.CharField(max_length=200, verbose_name="Código", default="0")
    name = models.CharField(max_length=200, verbose_name="Nombre", default="")
    phone = models.CharField(max_length=200, verbose_name="Phone", default="")
    email = models.CharField(max_length=200, verbose_name="Email", default="")
    dni = models.CharField(max_length=20, verbose_name="DNI", default="")
    address = models.CharField(max_length=255, verbose_name="Dirección", default="")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='Empresa', blank=True, null=True , related_name="clients")

    def __str__(self):
        return ("[%s] %s".format(self.code, self.name))

    class Meta:
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'
        ordering = ['name']

class Provider(models.Model):
    code = models.CharField(max_length=200, verbose_name="Código", default="0")
    name = models.CharField(max_length=200, verbose_name="Nombre", default="")
    phone = models.CharField(max_length=200, verbose_name="Phone", default="")
    email = models.CharField(max_length=200, verbose_name="Email", default="")
    company = models.ForeignKey(Company,on_delete=models.CASCADE,verbose_name='Empresa',blank=True,null=True,related_name="providers")

    ext_code = models.CharField(max_length=200, verbose_name="Ext code", default="")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Provider'
        verbose_name_plural = 'Providers'
        ordering = ['name']

class Tax(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nombre", default="")
    percent = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Percent", default=0)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='Empresa', blank=True, null=True, related_name="taxes")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Tax'
        verbose_name_plural = 'Taxes'
        ordering = ['name']

class ProductType(models.Model):
    online = models.BooleanField(verbose_name = "Venta online", default=False)
    name = models.CharField(max_length=200, verbose_name="Nombre", default="")
    tax = models.ManyToManyField(Tax, verbose_name="Tax", blank=True, null=True)
#    lending = models.BooleanField(verbose_name = "Préstamo", default=False)
#    lending_all = models.BooleanField(verbose_name = "Préstamo comunitario", default=False)
#    uuid = models.CharField(max_length=200, verbose_name="UUID", default="")
#    parent = models.ForeignKey('self',on_delete=models.CASCADE,verbose_name='Parent',blank=True,null=True,related_name="children")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='Empresa', blank=True, null=True , related_name="producttypes")

    ext_code = models.CharField(max_length=200, verbose_name="Ext code", default="")

    def __str__(self):
        return self.name

#    def summary_cost(self):
#        cost = 0
#        for p in self.products.all():
#            cost += p.last_cost.pvp
#        return cost

class Product(models.Model):
    deprecated = models.BooleanField(verbose_name = "Deprecated", default=False)
    online = models.BooleanField(verbose_name = "Online", default=False)
    min_to_purchase = models.IntegerField(verbose_name="Mínimo para comprar", default=0)
    quantity = models.IntegerField(verbose_name="Cantidad a comprar", default=0)
    units_in_box = models.IntegerField(verbose_name="Unidades en cada caja", default=0)
    alta_date = models.DateTimeField('Fecha de alta', default=datetime.now, blank=True, null=True)
    baja_date = models.DateTimeField('Fecha de baja', default=datetime.max, blank=True, null=True)
    expiry_date = models.DateTimeField('Fecha de caducidad', default=datetime.now, blank=True, null=True)
    code = models.CharField(max_length=50, verbose_name="Código",  default="")
    name = models.CharField(max_length=200, verbose_name="Nombre", default="")
    extra1 = models.CharField(max_length=200, verbose_name="Extra 1 (o Autor)", default="", blank=True, null=True)
    extra2 = models.CharField(max_length=200, verbose_name="Extra 2", default="", blank=True, null=True)
    location = models.CharField(max_length=200, verbose_name= 'Ubicación', blank=True, default='')
    picture = models.ImageField(verbose_name = "Imagen", blank=True, null=True, upload_to="uploads/products")

    product_type = models.ForeignKey(ProductType, on_delete=models.SET_NULL, verbose_name="Tipo de Producto", blank=True, null=True, related_name="products")
    provider = models.ForeignKey(Provider , on_delete=models.SET_NULL,  verbose_name="Distribuidor", blank=True, null=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='Empresa', blank=True, null=True , related_name="products")
#    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.SET_NULL,  verbose_name="Laboratorio (o Editorial)", blank=True, null=True)
#    tags = models.ManyToManyField(Tag, verbose_name="Tags", blank=True, null=True)

    ext_code = models.CharField(max_length=200, verbose_name="Ext code", default="")

    def __str__(self):
        return "[{0}] - {1}".format(self.code, self.name)

    @property
    def last_pvp(self):
        pvp = self.prices.filter(sale=True).order_by('-date').first()
        return pvp.amount if pvp != None else -1

    @property
    def last_cost(self):
        pvp = self.prices.filter(sale=False).order_by('-date').first()
        return pvp.amount if pvp != None else -1

    @property
    def get_tax(self):
        try:
            return self.product_type.tax.first().percent
        except:
            return 0

    def get_stock(self):
        in_flow = StoreInflow.objects.filter(product=self).values("product__name").aggregate(total=Sum('quantity'))
        out_flow = StoreOutflow.objects.filter(product=self).values("product__name").aggregate(total=Sum('quantity'))
        try:
            total_in = float(in_flow['total'])
        except Exception as e:
            total_in = 0
        try:
            total_out = float(out_flow['total'])
        except Exception as e:
            total_out = 0
        return float(total_in - total_out)
#
#
#    @classmethod
#    def new_code(cls):
#        try:
#            code = random_string(6).upper()
#            while cls.objects.filter(code=code).exists():
#                code = random_string(6).upper()
#            return (code)
#        except:
#            return (random_string(6).upper())
#
#    @property
#    def get_tax(self):
#        try:
#            return self.product_type.tax.first().percent
#        except:
#            return 0
#
#    @property
#    def pvp_average(self):
#        try:
#            result = StoreOutflow.objects.filter(product=self).aggregate(Avg('unit_price'))
#            if result is None:
#                return(0.)
#            else:
#                return(result['unit_price__avg'])
#        except Exception as e:
#            print (show_exc(e))
#            return(0)
#
#    @property
#    def cost_average(self):
#        try:
#            result = StoreInflow.objects.filter(product=self, unit_price__gt = 0., reception_date__year = datetime.now().year ).aggregate(Avg('unit_price'))
#            result = result['unit_price__avg']
#            if result is None:
#                return(0.)
#            else:
#                return(result)
#        except Exception as e:
#            print (show_exc(e))
#            return(0)
#
#    @property
#    def last_pvp(self, date=datetime.now()):
#        try:
#            result = SalesPrice.objects.filter(product=self, to_date__gte = date).order_by('-from_date').first()
#            if result is None:
#                return(SalesPrice(pvp=0,min_units=0, from_date=datetime.date.min, to_date=datetime.date.max, product=self))
#            else:
#                return(result)
#        except Exception as e:
#            print (show_exc(e))
#            return(SalesPrice(pvp=0,min_units=0, from_date=datetime.date.min, to_date=datetime.date.max, product=self))
#
#    @property
#    def last_cost(self):
#        try:
#            result = CostPrice.objects.filter(product=self, from_date__lte = datetime.now()).order_by('-from_date').first()
#            if result is None:
#                return(CostPrice(pvp=0,min_units=0, from_date=datetime.date.min, to_date=datetime.date.max, product=self))
#            else:
#                return(result)
#        except:
#            return(CostPrice(pvp=0,min_units=0, from_date=datetime.date.min, to_date=datetime.date.max, product=self))
#
#    @property
#    def previus_cost(self):
#        try:
#            last_cost = self.last_cost
#            result = CostPrice.objects.filter(product=self).exclude(pvp = last_cost.pvp).order_by('-from_date').first()
#            if result is None:
#                return(CostPrice(pvp=0,min_units=0, from_date=datetime.date.min, to_date=datetime.date.max, product=self))
#            else:
#                return(result)
#        except:
#            return(CostPrice(pvp=0,min_units=0, from_date=datetime.date.min, to_date=datetime.date.max, product=self))
#
#    def get_stock(self, date=datetime.now() + datetime.timedelta(days=1)):
#        in_flow = StoreInflow.objects.filter(product=self, reception_date__lte = date.replace(hour=23,minute=59,second=59)).values("product__name").aggregate(total=Sum('quantity'))
#        out_flow = StoreOutflow.objects.filter(product=self, reception_date__lte = date.replace(hour=23,minute=59,second=59)).values("product__name").aggregate(total=Sum('quantity'))
#        try:
#            total_in = float(in_flow['total'])
#        except Exception as e:
#            total_in = 0
#        try:
#            total_out = float(out_flow['total'])
#        except Exception as e:
#            total_out = 0
#        return float(total_in - total_out)
#
#    def get_sales(self, date=datetime.now()):
#        out_flow = StoreOutflow.objects.filter(product=self, reception_date__gte = date).values("product__pk").aggregate(total=Sum('quantity'))
#        try:
#            total_out = int(out_flow['total'])
#        except:
#            total_out = 0
#        return int(total_out)
#
#
#    @property
#    def in_stock(self):
#        return (self.get_stock(date=datetime.now() + datetime.timedelta(days=30)))
#
#    @property
#    def profit(self):
#        if self.last_cost.pvp != 0:
#            return ((float((self.last_pvp.pvp / self.last_cost.pvp)) - 1) * 100.)
#        else:
#            return (100.)
#
#    @property
#    def is_expired(self):
#        return self.expiry_date.date() < datetime.date.today()
#
#    def tojson(self):
#        try:
#            picture_url = ""
#            if self.picture:
#                picture_url = self.picture.url
#            product_type = ""
#            if self.product_type:
#                product_type = self.product_type.name
#            return {"name":self.name, "code":self.code, "units_in_box":self.units_in_box, "picture":picture_url,
#                    "pvp":float(self.last_pvp.pvp), "type":product_type, "tax":self.get_tax}
#        except Exception as e:
#            return {"error-msg":show_exc(e)}

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['name']

class StoreInflow(models.Model):
    quantity = models.IntegerField(verbose_name="Quantity", default=0)
    tax = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Tax", default=0) #DEPRECATED
    discount = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Discount", default=0) #DEPRECATED
    unit_price = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Unit Price", default=0) #DEPRECATED
    delivery_date = models.DateTimeField('Delivery date', default=datetime.now, blank=True, null=True) #DEPRECATED
    order_date = models.DateTimeField('Order date', default=datetime.now, blank=True, null=True) #DEPRECATED
    reception_date = models.DateTimeField('Reception date', default=datetime.now, blank=True, null=True) #DEPRECATED
    ref = models.CharField(max_length=200, verbose_name="Ref", default="") #DEPRECATED
    comments = models.CharField(max_length=200, verbose_name="Comentarios", default="") #DEPRECATED

    product = models.ForeignKey(Product,on_delete=models.SET_NULL,verbose_name="Producto",blank=True,null=True,related_name="inflows")
    #store = models.ForeignKey(Store, on_delete=models.SET_NULL, verbose_name="Almacén", blank=True, null=True)
    #purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, verbose_name="Purchase", blank=True, null=True, related_name="inflows")

    def __unicode__(self):
        return self.ref

    class Meta:
        verbose_name = 'Store Inflow'
        verbose_name_plural = 'Store Inflows'
        ordering = ['-id']

class StoreOutflow(models.Model):
    quantity = models.IntegerField(verbose_name="Quantity", default=0)
    tax = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Tax", default=0) #DEPRECATED
    unit_price = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Unit Price", default=0) #DEPRECATED
    delivery_date = models.DateTimeField('Delivery date', default=datetime.now, blank=True, null=True) #DEPRECATED
    order_date = models.DateTimeField('Order date', default=datetime.now, blank=True, null=True) #DEPRECATED
    reception_date = models.DateTimeField('Reception date', default=datetime.now, blank=True, null=True) #DEPRECATED
    ref = models.CharField(max_length=200, verbose_name="Ref", default="") #DEPRECATED
    comments = models.CharField(max_length=200, verbose_name="Comentarios", default="") #DEPRECATED

    client = models.ForeignKey(Client, on_delete=models.SET_NULL, verbose_name="Client", blank=True, null=True)
    product = models.ForeignKey(Product,on_delete=models.SET_NULL,verbose_name="Product",blank=True,null=True,related_name="outflows")
    #store = models.ForeignKey(Store, on_delete=models.SET_NULL, verbose_name="Store", blank=True, null=True)

    def __str__(self):
        return self.ref

    class Meta:
        verbose_name = 'Store Outflow'
        verbose_name_plural = 'Store Outflows'
        ordering = ['-id']

class Price(models.Model):
    sale = models.BooleanField(verbose_name = "Venta online", default=False)
    amount = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Pvp", default=0)
    date = models.DateTimeField('Date', default=datetime.now, blank=True, null=True)

    product = models.ForeignKey(Product,on_delete=models.SET_NULL,verbose_name="Product",blank=True,null=True,related_name="prices")
    #clients = models.ManyToManyField(Client, verbose_name="Clients", blank=True, related_name="sales_price_client")

    def __unicode__(self):
        return self.pvp

    class Meta:
        verbose_name = 'Sales price'
        verbose_name_plural = 'Sales prices'


'''
    Invoices
'''
class DeliveryNote(models.Model):
    paid = models.BooleanField(verbose_name="Paid", default=False)
    payment_date = models.DateTimeField('From date', default=datetime.max, blank=True, null=True)

    client = models.ForeignKey(Client, on_delete=models.SET_NULL, verbose_name="Client", blank=True, null=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='Empresa', blank=True, null=True , related_name="deliverynotes")

    def __unicode__(self):
        return self.payment_date

    class Meta:
        verbose_name = 'Delivery note'
        verbose_name_plural = 'Delivery notes'

class DeliveryNoteLine(models.Model):
    units = models.IntegerField(verbose_name="Units", default=0)
    unit_price = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Unit Price", default=0)
    discount = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Discount", default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Discount Percent", default=0)
    tax = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Tax", default=0)

    delivery_note = models.ForeignKey(DeliveryNote, on_delete=models.CASCADE, verbose_name="Delivery Note", blank=True, null=True)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, verbose_name="Product", blank=True, null=True)

    def __unicode__(self):
        return self.units

    class Meta:
        verbose_name = 'Delivery note line'
        verbose_name_plural = 'Delivery note lines'

class Invoice(models.Model):
    paid = models.BooleanField(verbose_name="Paid", default=False)
    cash = models.BooleanField(verbose_name="Cash", default=True) # Cash / Card
    regulated = models.BooleanField(verbose_name="Regulated", default=False) # Receta / Venta libre
    number = models.IntegerField(verbose_name="Number", default=0)
    paid_amount = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Paid amount", default=0)
    diff_amount = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Diff amount", default=0)
    date = models.DateTimeField('Invoice date', default=datetime.now, blank=True, null=True)
    payment_date = models.DateTimeField('From date', default=datetime.max, blank=True, null=True)
    hashinv = models.CharField(max_length=50, verbose_name="Hash", default="")
    typeinv = models.CharField(max_length=50, verbose_name="Type", default="PRETPV")
    client_name = models.CharField(max_length=255, verbose_name="Client name", default="")
    client_dni = models.CharField(max_length=255, verbose_name="Client dni", default="")
    client_addr = models.CharField(max_length=255, verbose_name="Client addr", default="")

    client = models.ForeignKey(Client, on_delete=models.SET_NULL, verbose_name="Client", blank=True, null=True)
    company = models.ForeignKey(Company,on_delete=models.CASCADE,verbose_name='Empresa',blank=True,null=True,related_name="invoices")

    def __unicode__(self):
        return self.payment_date

    @classmethod
    def next_number(cls, company, mtype="UNKNOWN"):
        try:
            invoices = cls.objects.filter(typeinv = mtype, company=company).order_by('number');
            if invoices.count() > 0:
                return (invoices.last().number + 1)
            return (datetime.now().year * 100000 + 1)
        except Exception as e:
            return (datetime.now().year * 100000 + 1)

    @classmethod
    def newhash(cls, length=10):
        try:
            hashinv = get_random_str(length)
            while cls.objects.filter(hashinv=hashinv).exists():
                hashinv = get_random_str(length)
            return (hashinv)
        except Exception as e:
            hashinv = get_random_str(100)
            return (hashinv)

    def total(self):
        try:
            total = 0.
            for line in self.lines.all():
                total += line.total
            return total
        except Exception as e:
            print (show_exc(e))
            return 0.

    def get_quantity(self):
        try:
            total = 0
            for line in self.lines.all():
                total += line.units
            return total
        except Exception as e:
            print (show_exc(e))
            return 0

    def get_taxes(self):
        try:
            total = 0
            for line in self.lines.all():
                total += line.get_taxes
            return total
        except Exception as e:
            print (show_exc(e))
            return 0

    def get_discount(self):
        try:
            total = 0.
            for line in self.lines.all():
                total += line.get_discount
            return total
        except Exception as e:
            print (show_exc(e))
            return 0

    def get_base(self):
        try:
            total = 0
            for line in self.lines.all():
                total += line.get_base
            return total
        except Exception as e:
            print (show_exc(e))
            return 0

    def to_json(self):
        try:
            result = serialize('json', [self])
            json_dic = json.loads(result)[0]
            json_dic["lines"] = json.loads(serialize('json', self.lines.all()))
        except Exception as e:
            print (show_exc(e))
            result = serialize('json', [self])
            json_dic = json.loads(result)
        return (json_dic)


    class Meta:
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'

class InvoiceLine(models.Model):
    units = models.IntegerField(verbose_name="Units", default=0)
    unit_price = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Unit Price", default=0)
    discount = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Discount", default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Discount Percent", default=0)
    tax = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Tax", default=0)

    delivery_note = models.ForeignKey(DeliveryNote, on_delete=models.CASCADE, verbose_name="Delivery Note", blank=True, null=True)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, verbose_name="Product", blank=True, null=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, verbose_name="Invoice", blank=True, null=True, related_name='lines')

    def __unicode__(self):
        return self.units

    @property
    def total(self):
        try:
            return self.get_base + self.get_taxes + self.get_discount
        except Exception as e:
            print (show_exc(e))
            return 0.

    @property
    def get_taxes(self):
        try:
            return self.get_base * (float(self.tax) * 0.01)
        except Exception as e:
            print (show_exc(e))
            return 0.

    @property
    def get_discount(self):
        try:
            return (-1) * (float(self.discount) + 0.01 * float(self.discount_percent) * float(self.units) * float(self.unit_price))
        except Exception as e:
            return show_exc(e)

    @property
    def get_base(self):
        try:
            return float(self.units) * float(self.unit_price)
        except Exception as e:
            return show_exc(e)

    class Meta:
        verbose_name = 'Invoice line'
        verbose_name_plural = 'Invoice lines'
        ordering = ['product__code','pk']

