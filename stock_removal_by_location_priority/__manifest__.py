{
    'name': 'Stock Removal by Location priority',
    'version': "15.0.1.0.0",
    'category': 'Warehouse Management',
    'sequence': 14,
    'summary': '',
    'author': 'Eficent, ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'images': [
    ],
    'depends': [
        'stock',
    ],
    'data': [
        'views/product_category_views.xml',
        'views/stock_location_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'pre_init_hook': 'pre_init_hook',
}
