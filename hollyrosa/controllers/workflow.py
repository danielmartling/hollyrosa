# -*- coding: utf-8 -*-
"""
Copyright 2010, 2011 Martin Eliasson

This file is part of Hollyrosa

Hollyrosa is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Hollyrosa is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with Hollyrosa.  If not, see <http://www.gnu.org/licenses/>.

"""

from tg import expose, flash, require, url, request, redirect,  validate
from repoze.what.predicates import Any, is_user, has_permission
from hollyrosa.lib.base import BaseController
from hollyrosa.model import genUID,  holly_couch
from sqlalchemy import and_
import datetime

#...this can later be moved to the VisitingGroup module whenever it is broken out
from tg import tmpl_context



from hollyrosa.widgets.edit_visiting_group_form import create_edit_visiting_group_form
from hollyrosa.widgets.edit_booking_day_form import create_edit_booking_day_form
from hollyrosa.widgets.edit_new_booking_request import  create_edit_new_booking_request_form
from hollyrosa.widgets.edit_book_slot_form import  create_edit_book_slot_form
from hollyrosa.widgets.validate_get_method_inputs import  create_validate_schedule_booking,  create_validate_unschedule_booking

from booking_history import  remember_workflow_state_change
from hollyrosa.controllers.common import workflow_map,  getLoggedInUser
from formencode import validators

__all__ = ['Workflow']

workflow_submenu = """<ul class="any_menu">
        <li><a href="overview">overview</a></li>
        <li><a href="view_preliminary">preliminary</a></li>
        <li><a href="view_nonapproved">non-approved</a></li>
        <li><a href="view_unscheduled">unscheduled</a></li>
        <li><a href="view_scheduled">scheduled</a></li>
        <li><a href="view_disapproved">dissapproved</a></li>
    </ul>"""

class Workflow(BaseController):
    def view(self, url):
        """Abort the request with a 404 HTTP status code."""
        abort(404)
    
    
    @expose('hollyrosa.templates.workflow_overview')
    def overview(self):
        """Show an overview of all bookings"""
        bookings = DBSession.query(booking.Booking).filter('booking_state > -100').all()
        scheduled_bookings = list()
        unscheduled_bookings = list()
        
        for b in bookings:
            if None == b.booking_day_id:
                unscheduled_bookings.append(b)
            else:
                scheduled_bookings.append(b)
        return dict(scheduled_bookings=scheduled_bookings,  unscheduled_bookings=unscheduled_bookings,  workflow_map=workflow_map,  workflow_submenu=workflow_submenu)
        
        
    @expose('hollyrosa.templates.workflow_view_scheduled')
    def view_nonapproved(self):
        scheduled_bookings = DBSession.query(booking.Booking).filter(and_('booking_state < 20', 'booking_state > -100', 'booking_day_id is not NULL')).all()
        return dict(scheduled_bookings=scheduled_bookings,  workflow_map=workflow_map, result_title='Unapproved scheduled bookings',  workflow_submenu=workflow_submenu)
    
    @expose('hollyrosa.templates.workflow_view_scheduled')
    def view_preliminary(self):
        scheduled_bookings = DBSession.query(booking.Booking).filter(and_('booking_state < 10', 'booking_state > -100', 'booking_day_id is not NULL')).all()
        return dict(scheduled_bookings=scheduled_bookings,  workflow_map=workflow_map, result_title='Preliminary scheduled bookings',  workflow_submenu=workflow_submenu)
    
    @expose('hollyrosa.templates.workflow_view_scheduled')
    def view_scheduled(self):
        scheduled_bookings = DBSession.query(booking.Booking).filter(and_('booking_day_id is not NULL', 'booking_state > -100')).all()
        return dict(scheduled_bookings=scheduled_bookings,   workflow_map=workflow_map, result_title='Schedueld bookings',  workflow_submenu=workflow_submenu)
        
        
    @expose('hollyrosa.templates.workflow_view_scheduled')
    def view_disapproved(self):
        scheduled_bookings = DBSession.query(booking.Booking).filter(and_('booking_state < 0', 'booking_state > -100', 'booking_day_id is not NULL')).all()
        return dict(scheduled_bookings=scheduled_bookings,   workflow_map=workflow_map, result_title='Disapproved bookings', workflow_submenu=workflow_submenu)
    
    
    @expose('hollyrosa.templates.workflow_view_unscheduled')
    def view_unscheduled(self):
        unscheduled_bookings = DBSession.query(booking.Booking).filter(and_('booking_day_id is NULL','booking_state > -100')).all()
        return dict(unscheduled_bookings=unscheduled_bookings,  workflow_map=workflow_map, result_title='Unscheduled bookings', workflow_submenu=workflow_submenu)
    
    def do_set_state(self, booking_id,  booking_o,  state):
        
        #...only PL can set state=20 (approved) or -10 (disapproved)
        print booking_o
        if state=='20' or state=='-10' or booking_o['booking_state'] == 20 or booking_o['booking_state']==-10:
            ok = False
            for group in getLoggedInUser(request).groups:
                if group.group_name == 'pl':
                    ok = True
            if not ok:
                flash('Only PL can do that. %s' % request.referrer, 'warning')
                raise redirect(request.referrer)
            
        ####remember_workflow_state_change(booking=booking_o,  state=state)
        booking_o['booking_state'] = state
        booking_o['ast_changed_by_id'] = getLoggedInUser(request).user_id
        holly_couch[booking_id] = booking_o

    @expose()
    @validate(validators={'booking_id':validators.UnicodeString(not_empty=True), 'state':validators.Int(not_empty=True), 'all':validators.Int(not_empty=False)})    
    #@require(Any(is_user('root'), has_permission('staff'), has_permission('pl'),  msg='Only PL or staff members can change booking state, and only PL can approve/disapprove'))
    def set_state(self,  booking_id=None,  state=0, all=0):
        if all == 0 or all==None:
            booking_o = holly_couch[booking_id] #DBSession.query(booking.Booking).filter('id='+str(booking_id)).one()
            self.do_set_state(booking_id,  booking_o, state)
        elif all == '1': # look for all bookings with same group
           booking_o = holly_couch[booking_id] #DBSession.query(booking.Booking).filter('id='+str(booking_id)).one()
           bookings = [ ] # Fix later DBSession.query(booking.Booking).filter(and_('visiting_group_id='+str(booking_o.visiting_group_id), 'activity_id='+str(booking_o.activity_id), 'booking_state > -100')).all()
           for new_b in bookings:
               if (new_b.content.strip() == booking_o.content.strip()) and (new_b.booking_day_id != None):
                   self.do_set_state(new_b._id,  new_b, state)
        else:
            pass        
        raise redirect(request.referrer)

       
    
