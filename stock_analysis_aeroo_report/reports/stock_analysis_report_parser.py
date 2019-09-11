##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models, _
from odoo.tools.safe_eval import safe_eval
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math


def base_round(num, base=5):
    return int(math.ceil(num/(base*1.0))*base)


def smart_round(num):
    if num > 20000:
        return base_round(num, 5000)
    elif num > 10000:
        return base_round(num, 2500)
    elif num > 5000:
        return base_round(num, 1000)
    elif num > 2000:
        return base_round(num, 500)
    elif num > 1000:
        return base_round(num, 250)
    elif num > 500:
        return base_round(num, 100)
    elif num > 200:
        return base_round(num, 50)
    elif num > 100:
        return base_round(num, 25)
    elif num > 50:
        return base_round(num, 10)
    else:
        return base_round(num, 5)


# Get a list of months names starting from the from_date
def get_last_months(from_date, to_date=False):
    if not to_date:
        to_date = datetime.today()
    curr_date = from_date
    while curr_date <= to_date:
        yield curr_date.strftime('%B %Y')
        curr_date += relativedelta(months=1)


class Parser(models.AbstractModel):
    _inherit = 'report.report_aeroo.abstract'
    _name = 'report.stock_analysis_report_parser'

    @api.model
    def aeroo_report(self, docids, data):
        if not data:
            data = {}

        self.context = self.env.context
        self.config = dict(self.context)
        self.from_date = self.context.get('from_date')
        self.to_date = self.context.get('to_date')
        self.months = list(get_last_months(
            datetime.strptime(self.from_date, '%Y-%m-%d'),
            datetime.strptime(
                self.to_date,
                '%Y-%m-%d'
            ) if self.to_date else False))

        domain = self.context.get('filter_domain')
        self.domain = safe_eval(domain) if domain else []

        data.update({
            'config': self.config,
            'from_date': self.from_date,
            'to_date': self.to_date,
            'months': self.months,
            'get_data': self.get_data,
            })

        return super().aeroo_report(docids, data)

    def get_data(self):

        # get products
        domain = self.domain
        domain.append(('active', '=', 1))
        domain.append(('type', '=', 'product'))
        product_ids = self.env['product.product'].search(
            domain, order='categ_id, default_code, name')

        # prepare stock move domains
        common_domain = []
        common_domain.append(('state', '=', 'done'))
        if self.context.get('from_date'):
            common_domain.append(('date', '>=', self.context.get('from_date')))
        if self.context.get('to_date'):
            common_domain.append(('date', '<', self.context.get('to_date')))

        # out domain
        out_domain = list(common_domain)
        if self.context.get('location_id'):
            out_domain.append(
                ('location_id', '=', self.context.get('location_id')))
        else:
            out_domain.append(
                ('location_dest_id.usage', 'in', ['internal']))

        # in domain
        in_domain = list(common_domain)
        if self.context.get('location_id'):
            in_domain.append(
                ('location_dest_id', '=', self.context.get('location_id')))
        else:
            in_domain.append(('location_id.usage', 'not in', ['internal']))

        # compile information
        res = []
        for p in product_ids:

            # get moves month by month
            odomain = list(out_domain)
            idomain = list(in_domain)
            odomain.append(('product_id', '=', p.id))
            idomain.append(('product_id', '=', p.id))
            om = self.env['stock.move'].read_group(
                odomain,
                groupby='date:month',
                fields=['product_id', 'date', 'product_qty'])
            im = self.env['stock.move'].read_group(
                idomain,
                groupby='date:month',
                fields=['product_id', 'date', 'product_qty'])

            # compile month by month dict
            months = dict((el, 0) for el in self.months)
            for m in om:
                months[m['date:month']] = \
                    months.get(m['date:month'], 0) + m['product_qty']
            for m in im:
                months[m['date:month']] = \
                    months.get(m['date:month'], 0) - m['product_qty']

            r = {
                'product_id': p,
                'default_code': p.default_code,
                'name': p.name,
                'reordering_min_qty': int(p.reordering_min_qty),
                'reordering_max_qty': int(p.reordering_max_qty),
                'seller_delay': max([s.delay for s in p.seller_ids] or [30]),
                'qty_available': p.qty_available,
                'months': months,
            }

            # moves by month
            # compile data for analysis
            month_data = [months.get(el, 0) for el in self.months]
            # remove zero or lower readings
            data = list(filter(lambda x: x > 0, month_data))
            # avg remaining data
            monthly = \
                round(sum(data)/(len(data)*1.0), 0) if len(data) > 0 else 0.0
            r['monthly'] = monthly

            calculated_min = max([((r['seller_delay']*1.3)/30), 1])*monthly
            r['suggested_min'] = smart_round(calculated_min)
            r['suggested_max'] = smart_round(calculated_min*2)
            r['stock_months'] = round(r['qty_available'] / monthly, 1) \
                if monthly > 0 else \
                ('Infinito' if r['qty_available'] > 0 else False)

            r['obs_stock'] = ''
            r['obs_stock'] = _('LOW STOCK') if (
                (r['qty_available']) < r['suggested_min']) else r['obs_stock']

            r['obs_stock'] = _('OVERSTOCK') if (
                (r['qty_available']) > r['suggested_max']) else r['obs_stock']

            res.append(r)

        # Filter according to context
        # TODO: Implement filters based on stock analysis
        # if self.config_filter == 'not_ok':
        #     res = filter(lambda x: x.get('obs') != '', res)
        # if self.config_filter == 'only_low':
        #     res = filter(lambda x: 'LOW' in x.get('obs'), res)
        # if self.config_filter == 'low_stock':
        #     res = filter(lambda x: x.get('obs_stock') != '', res)

        return res
