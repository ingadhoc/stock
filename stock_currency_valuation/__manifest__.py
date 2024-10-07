{
    'name': 'Stock currency valuation',
    'version': "16.0.1.0.0",
    'category': 'Warehouse Management',
    'sequence': 14,
    'summary': '',
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'images': [
    ],
    'depends': [
        'stock_account',
        'product_replenishment_cost',
    ],
    'data': [
        'views/product_category.xml',
        'views/product.xml',
        'views/stock_valuation_layer.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'assets': {
    },
    'license': 'AGPL-3',
}
