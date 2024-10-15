from django.conf import settings

import stripe

def show_exc(e):
    import sys
    exc_type, exc_obj, exc_tb = sys.exc_info()
    return ("ERROR ===:> [%s in %s:%d]: %s" % (exc_type, exc_tb.tb_frame.f_code.co_filename, exc_tb.tb_lineno, str(e)))

class ShStripe:
    def __init__(self, api_key="", domain_name="capsulae.org"):
        self.api_key = api_key
        self.domain_name = domain_name
        try:
            self.return_url = settings.STRIPE_RETURN_URL
            self.success_url = settings.STRIPE_SUCCESS_URL
            self.cancel_url = settings.STRIPE_CANCEL_URL
            self.return_pay_url = settings.STRIPE_RETURN_PAY_URL
        except:
            self.return_url = ""
            self.success_url = ""
            self.cancel_url = ""
            self.return_pay_url = ""


    def create_stripe_payment_intent(self, customer_id, payment_method_id, amount, currency="eur"):
        stripe.api_key = self.api_key

        try:
            next_action = ""
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                customer=customer_id,
                payment_method=payment_method_id,
                automatic_payment_methods={ 'enabled': True, },
                setup_future_usage='on_session',
                return_url=self.return_pay_url,
                confirm=True
            )
            if payment_intent.next_action != None:
                if payment_intent.next_action.redirect_to_url != None:
                    next_action = payment_intent.next_action.redirect_to_url.url

            return payment_intent.id, next_action
        except stripe.error.StripeError as e:
            print(f"Error creating Stripe payment intent: {e}")
            return None

    def get_session (self, session_id):
        stripe.api_key = self.api_key
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            return session
        except stripe.error.StripeError as e:
            print(f"Error getting Stripe session: {e}")
            return None

    def verify_payment_intent(self, payment_intent_id):
        stripe.api_key = self.api_key
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return payment_intent
        except stripe.error.StripeError as e:
            print(f"Error verifying Stripe payment intent: {e}")
            return None

    def get_subscription(self, subscription_id):
        stripe.api_key = self.api_key
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return subscription
        except stripe.error.StripeError as e:
            print(f"Error getting Stripe subscription: {e}")
            return None

    def get_product(self, product_id):
        stripe.api_key = self.api_key
        try:
            product = stripe.Product.retrieve(product_id)
            return product
        except stripe.error.StripeError as e:
            print(f"Error getting Stripe product: {e}")
            return None
        
    def create_fundec_suscription_url(self, pvp, myuuid, period="month"):
        print(f"Creating Stripe subscription for {pvp} {period}")
        stripe.api_key = self.api_key
        try:
            product = stripe.Product.create(
                name=f"Donación personalizada {myuuid}",
                type="service",                
            )

            price = stripe.Price.create(
                unit_amount=pvp,
                currency="eur",
                recurring={"interval": period},
                product=product.id,
            )

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": price.id,
                        "quantity": 1,

                    },
                ],
                mode="subscription",
                billing_address_collection='required',

                success_url=f"https://{self.domain_name}/account/payment-stripe-verify/{{CHECKOUT_SESSION_ID}}/",
                cancel_url=f"https://{self.domain_name}/account/payment-error/",
            )

            return f"{session.url}"
        except stripe.error.StripeError as e:
            print(f"Error creating Stripe subscription: {e}")
            return f"https://{self.domain_name}/account/payment-error/"


