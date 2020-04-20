# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    duplicate_have = fields.Boolean(default=False)
    duplicate_ids = fields.Many2many('res.partner', compute='_find_contact_duplicates')
    duplicate_len = fields.Integer(compute='_find_contact_duplicates')

    @api.model
    def create(self, vals):
        if not self._get_duplicate_check():
            res = super(ResPartner, self).create(vals)
        else:
            fields_to_check = self._get_duplicate_check_fields()
            if fields_to_check:
                duplicates = self.find_duplicate_by_fields(vals, fields_to_check)
                if duplicates and not self.check_user_in_whitelist():
                    dups_to_err = self.create_dups_error_message(fields_to_check, duplicates, vals)
                    str_to_err = self._create_error_str(dups_to_err)
                    raise UserError(_(str_to_err))
                res = super(ResPartner, self).create(vals)
                if duplicates and self.check_user_in_whitelist():
                    for duplicate_field in duplicates:
                        for duplicate in duplicate_field:
                            if not duplicate.duplicate_have:
                                duplicate.duplicate_have = True
                    res.duplicate_have = True
        return res

    def write(self, vals):
        if not self._get_duplicate_check():
            res = super(ResPartner, self).write(vals)
        else:
            res = super(ResPartner, self).write(vals)
            fields_to_check = self._get_duplicate_check_fields()
            if fields_to_check:
                duplicates = self.find_duplicate_by_object(fields_to_check)
                if duplicates and not self.check_user_in_whitelist():
                    dups_to_err = self.create_dups_error_message(fields_to_check, duplicates)
                    str_to_err = self._create_error_str(dups_to_err)
                    raise UserError(_(str_to_err))
                if duplicates and self.check_user_in_whitelist():
                    for duplicate_field in duplicates:
                        for duplicate in duplicate_field:
                            if not duplicate.duplicate_have:
                                duplicate.duplicate_have = True
                    if not self.duplicate_have:
                        self.duplicate_have = True
        return res

    def action_get_duplicates_tree_view(self):
        action = self.env.ref('contacts.action_contacts').read()[0]
        action['domain'] = [('id', 'in', self.duplicate_ids.ids)]
        action['context'] = dict(self._context)
        return action

    def _find_contact_duplicates(self):
        fields_to_check = self._get_duplicate_check_fields()
        dups = self.env['res.partner'].browse([])
        for f in fields_to_check:
            dup = self.env['res.partner'].search([(f.field, '=', getattr(self, f.field)), ('id', '!=', self.id), (f.field, '!=', False)])
            dups += dup
        if dups:
            self.duplicate_ids = dups
            self.duplicate_len = len(dups)
            if not self.duplicate_have:
                self.duplicate_have = True
        else:
            if self.duplicate_have:
                self.duplicate_have = False
            self.duplicate_len = 0

    def find_duplicate_by_fields(self, vals_list, fields_to_check):
        result = []
        self.env.context = dict(self.env.context)
        self.env.context['dup_fields'] = []
        for f in fields_to_check:
            dups = self.env['res.partner'].search([(f.field, '=', vals_list.get(f.field)), (f.field, '!=', False)])
            if dups:
                self.env.context['dup_fields'].append(f.field)
                result.append(dups)
        return result

    def find_duplicate_by_object(self, fields_to_check):
        result = []
        self.env.context = dict(self.env.context)
        self.env.context['dup_fields'] = []
        for f in fields_to_check:
            dups = self.env['res.partner'].search([(f.field, '=', getattr(self, f.field)), ('id', '!=', self.id), (f.field, '!=', False)])
            if dups:
                self.env.context['dup_fields'].append(f.field)
                result.append(dups)
        return result

    def create_dups_error_message(self, fields_to_check, dups, vals_list=None):
        dups_to_str = []
        dup_fields = self.env.context.get('dup_fields', [])
        for index in range(len(dups)):
            dups_to_str.append([dup_fields[index], dups[index].mapped('name'), dups[index].mapped('id')]) 
        return dups_to_str
    
    def check_user_in_whitelist(self):
        users = self._get_duplicate_whitelist()
        if not self.env.user in users:
            return False
        return True
        

    @api.model
    def _create_error_str(self, duplicates):
        result_str = ""
        for field in duplicates:
            result_str += f"Duplicates were found for the field '{field[0]}':\n"
            for index in range(len(field[1])):
                result_str += f"{index+1}) {field[1][index]} (ID={field[2][index]});\n"
        return result_str
        
    @api.model
    def _get_duplicate_check(self):
        return self.env['ir.config_parameter'].sudo().get_param('contact_deduplicate.duplicate_check')

    @api.model
    def _get_duplicate_check_fields(self):
        f_ids = self.env['ir.config_parameter'].sudo().get_param('contact_deduplicate.duplicate_check_fields')
        f_ids = eval(f_ids) if f_ids else []
        fields = self.env['res.partner.fields'].browse(f_ids)
        return fields
    
    @api.model
    def _get_duplicate_whitelist(self):
        u_ids = self.env['ir.config_parameter'].sudo().get_param('contact_deduplicate.user_whitelist')
        u_ids = eval(u_ids) if u_ids else []
        users = self.env['res.users'].browse(u_ids)
        return users