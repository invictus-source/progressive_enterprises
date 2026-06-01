from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date,
    ForeignKey, Text, Enum, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    full_name = Column(String(128), nullable=False)
    role = Column(Enum("developer", "admin", "staff", name="user_role"), nullable=False, default="staff")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    phone = Column(String(20), nullable=False)
    alt_phone = Column(String(20), nullable=True)
    email = Column(String(128), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(64), nullable=True)
    gstin = Column(String(20), nullable=True)
    id_proof_type = Column(String(32), nullable=True)
    id_proof_no = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)

    sales = relationship("Sale", back_populates="customer")
    payments = relationship("Payment", back_populates="customer")
    emi_records = relationship("EMIRecord", back_populates="customer")

    def __repr__(self):
        return f"<Customer {self.name}>"


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    phone = Column(String(20), nullable=False)
    alt_phone = Column(String(20), nullable=True)
    email = Column(String(128), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(64), nullable=True)
    gstin = Column(String(20), nullable=True)
    bank_name = Column(String(64), nullable=True)
    bank_account = Column(String(32), nullable=True)
    bank_ifsc = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)

    purchases = relationship("Purchase", back_populates="vendor")
    payments = relationship("Payment", back_populates="vendor")

    def __repr__(self):
        return f"<Vendor {self.name}>"


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    brand = Column(String(64), nullable=True)
    model_no = Column(String(64), nullable=True)
    serial_number = Column(String(128), nullable=True)
    barcode = Column(String(64), nullable=True, unique=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    hsn_code = Column(String(16), nullable=True)
    gst_rate = Column(Float, default=18.0)
    purchase_price = Column(Float, default=0.0)
    selling_price = Column(Float, default=0.0)
    stock_qty = Column(Integer, default=0)
    min_stock = Column(Integer, default=2)
    unit = Column(String(16), default="Pcs")
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    category = relationship("Category", back_populates="products")
    sale_items = relationship("SaleItem", back_populates="product")
    purchase_items = relationship("PurchaseItem", back_populates="product")

    def __repr__(self):
        return f"<Product {self.name}>"


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_no = Column(String(32), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    sale_date = Column(DateTime, default=datetime.now)
    subtotal = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    taxable_amount = Column(Float, default=0.0)
    cgst_amount = Column(Float, default=0.0)
    sgst_amount = Column(Float, default=0.0)
    igst_amount = Column(Float, default=0.0)
    total_gst = Column(Float, default=0.0)
    grand_total = Column(Float, default=0.0)
    payment_mode = Column(Enum("Cash", "Card", "UPI", "EMI", "Mixed", name="payment_mode"), default="Cash")
    amount_received = Column(Float, default=0.0)
    balance_due = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_cancelled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    customer = relationship("Customer", back_populates="sales")
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    emi_record = relationship("EMIRecord", back_populates="sale", uselist=False)

    def __repr__(self):
        return f"<Sale {self.invoice_no} – ₹{self.grand_total}>"


class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_name = Column(String(128), nullable=False)
    qty = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False)
    discount_pct = Column(Float, default=0.0)
    gst_rate = Column(Float, default=18.0)
    taxable_amount = Column(Float, default=0.0)
    gst_amount = Column(Float, default=0.0)
    line_total = Column(Float, default=0.0)

    sale = relationship("Sale", back_populates="items")
    product = relationship("Product", back_populates="sale_items")


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    grn_no = Column(String(32), unique=True, nullable=False)
    bill_no = Column(String(64), nullable=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    purchase_date = Column(DateTime, default=datetime.now)
    subtotal = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    taxable_amount = Column(Float, default=0.0)
    cgst_amount = Column(Float, default=0.0)
    sgst_amount = Column(Float, default=0.0)
    igst_amount = Column(Float, default=0.0)
    total_gst = Column(Float, default=0.0)
    grand_total = Column(Float, default=0.0)
    payment_mode = Column(String(32), default="Cash")
    amount_paid = Column(Float, default=0.0)
    balance_due = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    vendor = relationship("Vendor", back_populates="purchases")
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Purchase {self.grn_no}>"


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_name = Column(String(128), nullable=False)
    qty = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False)
    gst_rate = Column(Float, default=18.0)
    taxable_amount = Column(Float, default=0.0)
    gst_amount = Column(Float, default=0.0)
    line_total = Column(Float, default=0.0)

    purchase = relationship("Purchase", back_populates="items")
    product = relationship("Product", back_populates="purchase_items")


class FinanceProvider(Base):
    __tablename__ = "finance_providers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), unique=True, nullable=False)
    contact_person = Column(String(128), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(128), nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    emi_records = relationship("EMIRecord", back_populates="finance_provider")


class EMIRecord(Base):
    __tablename__ = "emi_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    finance_provider_id = Column(Integer, ForeignKey("finance_providers.id"), nullable=False)
    loan_amount = Column(Float, nullable=False)
    down_payment = Column(Float, default=0.0)
    processing_fee = Column(Float, default=0.0)
    tenure_months = Column(Integer, nullable=False)
    monthly_installment = Column(Float, nullable=False)
    interest_rate = Column(Float, default=0.0)
    loan_account_no = Column(String(64), nullable=True)
    start_date = Column(Date, nullable=False)
    status = Column(Enum("Active", "Closed", "Defaulted", name="emi_status"), default="Active")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    sale = relationship("Sale", back_populates="emi_record")
    customer = relationship("Customer", back_populates="emi_records")
    finance_provider = relationship("FinanceProvider", back_populates="emi_records")
    emi_payments = relationship("EMIPayment", back_populates="emi_record", cascade="all, delete-orphan")


class EMIPayment(Base):
    __tablename__ = "emi_payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    emi_record_id = Column(Integer, ForeignKey("emi_records.id"), nullable=False)
    installment_no = Column(Integer, nullable=False)
    due_date = Column(Date, nullable=False)
    amount_due = Column(Float, nullable=False)
    paid_date = Column(Date, nullable=True)
    amount_paid = Column(Float, default=0.0)
    is_paid = Column(Boolean, default=False)
    penalty = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)

    emi_record = relationship("EMIRecord", back_populates="emi_payments")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_type = Column(Enum("receipt", "payment", name="payment_type"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"), nullable=True)
    amount = Column(Float, nullable=False)
    mode = Column(Enum("Cash", "Card", "UPI", "Cheque", "NEFT/RTGS", name="pay_mode"), default="Cash")
    reference_no = Column(String(64), nullable=True)
    payment_date = Column(DateTime, default=datetime.now)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    customer = relationship("Customer", back_populates="payments")
    vendor = relationship("Vendor", back_populates="payments")