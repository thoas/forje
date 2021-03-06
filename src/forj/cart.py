import simplejson as json

from django.db import transaction

from collections import defaultdict

from forj.models import Product, Order, OrderItem

CART_SESSION_KEY = "cart_id"


class Cart(object):
    def __init__(self):
        self._products = {}
        self.amount = 0
        self.shipping_cost = 0
        self.tax_cost = 0
        self.total = 0

    def add_product(self, reference, quantity=1):
        product = Product.objects.from_reference(reference)

        if product.pk not in self._products:
            self._products[product.pk] = {"obj": product, "refs": defaultdict(int)}

        self._products[product.pk]["refs"][reference] += quantity

        self.update()

    def remove_product(self, reference):
        product = Product.objects.from_reference(reference)

        if product.pk in self._products:
            del self._products[product.pk]["refs"][reference]

        if not self._products[product.pk]:
            del self._products[product.pk]

        self.update()

    def update(self):
        self.amount = 0
        self.shipping_cost = 0
        self.total = 0
        self.tax_cost = 0

        for product_id, result in self._products.items():
            for ref, quantity in result["refs"].items():
                amount = quantity * result["obj"].get_price(ref)
                shipping_cost = result["obj"].shipping_cost or 0
                shipping_cost = quantity * shipping_cost
                tax_cost = result["obj"].tax_cost or 0
                tax_cost = quantity * tax_cost

                self.amount += amount
                self.shipping_cost += shipping_cost
                self.tax_cost += tax_cost
                self.total += amount + shipping_cost + tax_cost

    @property
    def data(self):
        data = {}
        for product_id, result in self._products.items():
            data.update(result["refs"])

        return data

    def get_items(self):
        products = []

        for product_id, entry in self._products.items():
            product = entry["obj"]

            for ref, quantity in entry["refs"].items():
                total = quantity * product.get_price(ref)
                if product.shipping_cost:
                    total += quantity * product.shipping_cost
                if product.tax_cost:
                    total += quantity * product.tax_cost

                products.append(
                    {
                        "quantity": quantity,
                        "reference": ref,
                        "product": product,
                        "total": total,
                    }
                )

        return products

    @property
    def total_quantity(self):
        return sum([item["quantity"] for item in self.get_items()])

    @property
    def response(self):
        return {
            "items": self.get_items(),
            "total": self.total,
            "amount": self.amount,
            "shipping_cost": self.shipping_cost,
            "tax_cost": self.tax_cost,
        }

    @property
    def serialized_data(self):
        return json.dumps(self.data)

    @classmethod
    def from_serialized_data(cls, data):
        return cls.from_data(json.loads(data))

    @classmethod
    def from_data(cls, data):
        cart = cls()

        for reference, quantity in data.items():
            cart.add_product(reference, quantity)

        return cart

    @classmethod
    def from_request(cls, request):
        result = request.session.get(CART_SESSION_KEY)
        if result is None:
            return None

        return cls.from_serialized_data(result)

    @classmethod
    def flush(cls, request):
        if CART_SESSION_KEY not in request.session:
            return

        del request.session[CART_SESSION_KEY]

        return cls()

    def to_request(self, request):
        session = request.session
        session[CART_SESSION_KEY] = self.serialized_data
        session.save()

    @transaction.atomic
    def save(self, commit=True, order=None, defaults=None):
        defaults = defaults or {}

        self.update()

        if order is None:
            order = Order()

        order.amount = self.amount
        order.shipping_cost = self.shipping_cost
        order.tax_cost = self.tax_cost

        for k, v in defaults.items():
            setattr(order, k, v)

        order_items = []

        for product_id, result in self._products.items():
            product = result["obj"]

            for ref, quantity in result["refs"].items():
                shipping_cost = quantity * product.shipping_cost
                tax_cost = quantity * product.tax_cost

                order_item = OrderItem(
                    order=order,
                    quantity=quantity,
                    amount=quantity * product.get_price(ref),
                    product_reference=ref,
                    shipping_cost=shipping_cost,
                    tax_cost=tax_cost,
                    product=product,
                )
                order_items.append(order_item)

        if commit is True:
            if order.pk:
                order.items.all().delete()

            order.save()

            for order_item in order_items:
                order_item.order = order

            OrderItem.objects.bulk_create(order_items)

        return order
