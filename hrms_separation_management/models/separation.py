from odoo import models, fields, api
from datetime import date
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class HRMSSeparation(models.Model):
    _name = "hr.separation"
    _description = "Separation Management"
    _inherit = ["mail.thread", "mail.activity.mixin", "resource.mixin"]

    name = fields.Many2one('hr.employee', "Employee Name", required=True)
    department_id = fields.Many2one('hr.department', "Department", related="name.department_id")
    job_id = fields.Many2one('hr.job', "Job Position", related="name.job_id")
    parent_id = fields.Many2one('hr.employee', "Manager", related="name.parent_id")
    separation_type = fields.Selection([
        ('resignation', 'Resignation'),
        ('terminated_company', 'Termination(Company Initiated)'),
        ('terminated_infraction', 'Termination (Infraction)'),
        ('retirement', 'Retirement')
    ], string="Separation Type", required=True)
    resignation_letter = fields.Many2one('hr.resignation.letter',
                                         "Resignation Letter")
    reason = fields.Selection([
        ('underappreciated', 'Underappreciated (resignation)'),
        ('lack_of_proper_compensation', 'Lack of Proper Compensation (resignation)'),
        ('unrealistic_goals', 'Unrealistic Goals (resignation)'),
        ('lack_of_joy', 'Lack of a Joyful Environment (resignation)'),
        ('lack_of_work', 'lack of work/life balance (resignation)'),
        ('upward_mobility', 'No upward mobility (resignation)'),
        ('prioritize_health', 'Prioritize  health (retirement)'),
        ('caring_for_family', 'Caring for Family (retirement)'),
        ('violation', 'Violating Company Policy  (termination)'),
        ('poor_performance', 'Poor Performance (termination)'),
        ('misconduct', 'Misconduct (termination)'),
        ('insubordination', 'Insubordination (termination)')
    ], string="Reason", required=True)
    joined = fields.Date("Joined Date",  required=True)
    relieved = fields.Date("Relieved Date", required=True)
    date_raised = fields.Date("Raised on")
    date_of_request = fields.Date("Date of Request approval")
    note = fields.Text(string="Notes")

    iterview_form = fields.Many2one('survey.survey', 'Interview Form')
    quit_claim = fields.Boolean("Quit Claims")
    cert_of_employment = fields.Boolean(string="Certificate of Employment")
    details = fields.Boolean("2316 Details")
    loan = fields.Boolean("Loan Deduction Summary Table")
    clearance = fields.Boolean("Employee Clearance", default=False)

    date_submitted = fields.Date("Date Submitted")
    submitted_by = fields.Many2one('res.users', 'Submitted By')
    date_confirm = fields.Date("Date Confirmed")
    confirm_by = fields.Many2one('res.users', 'Confirmed By')
    date_approved = fields.Date("Date Approved")
    approved_by = fields.Many2one('res.users', 'Approved By')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('for_confirmation', 'Waiting for Confirmation'),
        ('for_approval', 'Waiting for Approval'),
        ('approve', 'Approved'),
        ('claim', 'Claimed')
    ], string="Status", default="draft", readonly=True, copy=False)

    @api.onchange('resignation_letter')
    def _separation_letter(self):
        if self.resignation_letter:
            self.relieved = self.resignation_letter.relieved
            self.reason = self.resignation_letter.reason

    @api.onchange('name')
    def _duplicate_employee_entry(self):
        if self.name:
            duplicate = self.search([('name', '=', self.name.id),
                                     ('id', '!=', self._origin.id),
                                     ('state', 'in', ('for_confirmation',
                                                      'for_approval',
                                                      'approve'))])
            if duplicate:
                return {
                    'warning': {
                        'title': "Duplicate Entry",
                        'message': """Duplicate Separation Request.
                        Please Check the other records for Reference"""
                    }
                }

    @api.constrains('name')
    def check_duplicate_true(self):
        for i in self:
            if i.name:
                duplicate = self.search([('name', '=', i.name.id),
                                         ('id', '!=', i.id),
                                         ('state', 'in', ('for_confirmation',
                                                          'for_approval',
                                                          'approve'))])
            if duplicate:
                raise UserError('''Duplicate Resignation Letter.
                                Please Check the other records for Reference''')


    @api.multi
    def generate_clearance(self):
        for rec in self:
            user_id = rec.env['res.users'].browse(rec._context.get('uid'))
            clearance = rec.env['hr.exit.clearance'].create({
                'name': rec.name.id,
                'separation_parent_id': rec.id,
            })

        return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'hr.exit.clearance',
                    'res_id': int(clearance.id),
                    'view_id': False,
                }
    @api.multi
    def employee_clearance(self):
        return {
                'name': ('Exit Clearance'),
                'domain': [('name', '=', self.name.id)],
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'view_id': False,
                'res_model': 'hr.exit.clearance',
                }
    @api.multi
    def submit(self):
        for rec in self:
            duplicate = rec.search([('name', '=', rec.name.id),
                                     ('id', '!=', rec.id),
                                     ('state', 'in', ('for_confirmation',
                                                      'for_approval',
                                                      'approve'))])
            if duplicate:
                raise UserError('''Duplicate Resignation Letter.
                                Please Check the other records for Reference''')
            else:
                rec.date_raised = date.today()
                rec.date_submitted = date.today()
                user_id = self.env['res.users'].browse(self._context.get('uid'))
                rec.submitted_by = user_id.id

        return self.write({'state': 'for_confirmation'})

    @api.multi
    def confirm(self):
        for i in self:
            i.date_confirm = date.today()
            user_id = self.env['res.users'].browse(i._context.get('uid'))
            i.confirm_by = user_id.id
        return self.write({'state': 'for_approval'})

    @api.multi
    def waiting_approve(self):
        for rec in self:
            rec.date_of_request = date.today()
            rec.date_approved = date.today()
            user_id = self.env['res.users'].browse(self._context.get('uid'))
            rec.approved_by = user_id.id
            if rec.resignation_letter:
                rec.resignation_letter.state = 'approve'
                rec.resignation_letter.separation_parent_id = rec.id
                rec.resignation_letter.date_approved = date.today()
                rec.resignation_letter.approved_by = user_id.id
        return self.write({'state': 'approve'})

    @api.multi
    def set_claim(self):
        return self.write({'state':'claim'})