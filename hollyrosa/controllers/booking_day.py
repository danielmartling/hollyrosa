# -*- coding: utf-8 -*-
"""
Copyright 2010, 2011, 2012 Martin Eliasson

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




Documentation pointers:
http://turbogears.org/2.0/docs/toc.html
http://toscawidgets.org/documentation/tw.forms/tutorials/index.html#constructing-a-form
http://turbogears.org/2.0/docs/main/ToscaWidgets/forms.html

http://toscawidgets.org/documentation/tw.dynforms/tutorial.html
http://pylonsbook.com/en/1.1/working-with-forms-and-validators.html
http://turbogears.org/2.1/docs/modules/thirdparty/formencode_api.html
http://blog.vrplumber.com/index.php?/archives/2381-ToscaWidgets-JQuery-and-TinyMCE-Tutorialish-ly.html
http://turbogears.org/2.0/docs/main/Auth/Authorization.html#module-repoze.what.predicates

"""


from tg import expose, flash, require, url, request, redirect,  validate
from repoze.what.predicates import Any, is_user, has_permission

from hollyrosa.lib.base import BaseController
from hollyrosa.model import DBSession, metadata,  booking,  holly_couch,  genUID,  get_visiting_groups, get_visiting_groups_at_date,  getBookingDays,  getAllActivities,  getSlotAndActivityIdOfBooking,  getBookingHistory
from sqlalchemy import and_, or_
from sqlalchemy.orm import eagerload,  eagerload_all
import datetime
from formencode import validators

#...this can later be moved to the VisitingGroup module whenever it is broken out
from tg import tmpl_context

import tw.tinymce

from hollyrosa.widgets.edit_visiting_group_form import create_edit_visiting_group_form
from hollyrosa.widgets.edit_booking_day_form import create_edit_booking_day_form
from hollyrosa.widgets.edit_new_booking_request import  create_edit_new_booking_request_form
from hollyrosa.widgets.edit_activity_form import create_edit_activity_form
from hollyrosa.widgets.edit_book_slot_form import  create_edit_book_slot_form
from hollyrosa.widgets.move_booking_form import  create_move_booking_form
from hollyrosa.widgets.validate_get_method_inputs import  create_validate_schedule_booking,  create_validate_unschedule_booking

from hollyrosa.controllers.booking_history import remember_booking_change,  remember_schedule_booking,  remember_unschedule_booking,  remember_book_slot,  remember_booking_properties_change,  remember_new_booking_request,  remember_booking_request_change,  remember_delete_booking_request,  remember_block_slot, remember_unblock_slot

from hollyrosa.controllers.common import workflow_map,  DataContainer,  getLoggedInUser,  change_op_map,  getRenderContent, getRenderContentDict,  computeCacheContent

__all__ = ['BookingDay',  'Calendar']
    

def getBookingDay(booking_day_id):
    return holly_couch[booking_day_id] 


def getBookingDayOfDate(date):
    map_fun = """function(doc) {
            if (doc.type == 'booking_day') {
                if (doc.date == '"""+str(date)+"""') {
            emit(doc._id, doc);
        }}}"""
    bookings_c =  holly_couch.query(map_fun)

    bookings = [b for b in bookings_c]
    return bookings[0].value
    
def getBooking(id):
    return holly_couch[id]
    


def deleteBooking(booking_o):
    booking_o['booking_state'] = -100
    booking_o['booking_day_id'] = ''
    booking_o['slot_id'] = ''
    holly_couch[booking_o['_id']] = booking_o

def make_booking_day_activity_anchor(tmp_activity_id):
    return '#activity_row_id_' + str(tmp_activity_id)


def getNextBookingDayId(booking_day):
    #booking_day_o = [ ]  DBSession.query(booking.BookingDay).filter('date=\''+(o_booking.booking_day.date + datetime.timedelta(1)
#).strftime('%Y-%m-%d')+'\'').one()
#    return booking_day_o.id
    this_date = booking_day['date'] # make date from string, but HOW?
    next_date = (datetime.datetime.strptime(this_date,'%Y-%m-%d') +  datetime.timedelta(1)).strftime('%Y-%m-%d')
    print 'next date',  next_date
    
    map_fun = """function(doc) {
            if (doc.type == 'booking_day') {
                if (doc.date == '"""+str(next_date)+"""') {
            emit(doc._id, doc);
        }}}"""
    
    booking_day_c =  holly_couch.query(map_fun)

    booking_days = [b for b in booking_day_c]
    return (booking_days[0].value)['_id']


        
    
class Calendar(BaseController):
    def view(self, url):
        """Abort the request with a 404 HTTP status code."""
        abort(404)
        

    @expose('hollyrosa.templates.calendar_overview')
    def overview_all(self):
        """Show an overview of all booking days"""
        #booking_days = DBSession.query(booking.BookingDay).all()
        return dict(booking_days=getBookingDays())


    @expose('hollyrosa.templates.calendar_overview')
    def overview(self):
        """Show an overview of all booking days"""
        ##booking_days = DBSession.query(booking.BookingDay).filter('date >=\''+datetime.date.today().strftime('%Y-%m-%d')+'\'').all()
        return dict(booking_days=getBookingDays(from_date=datetime.date.today().strftime('%Y-%m-%d')))
    

    @expose('hollyrosa.templates.calendar_upcoming')
    def upcoming(self):
        """Show an overview of all booking days"""
        today_date_str = datetime.date.today().strftime('%Y-%m-%d')
        end_date_str = (datetime.date.today()+datetime.timedelta(5)).strftime('%Y-%m-%d')
        booking_days = getBookingDays(from_date=today_date_str,  to_date=end_date_str) #DBSession.query(booking.BookingDay).filter(and_('date >=\'' + today_date_str +'\'','date < \'' + end_date_str +'\'')).order_by(booking.BookingDay.date).all()

        vgroups = get_visiting_groups(from_date=today_date_str,  to_date=end_date_str) #DBSession.query(booking.VisitingGroup).filter(or_('todate >= \''+ today_date_str +'\'','fromdate <= \''+ end_date_str  +'\'')).all()

        group_info = dict()
        for b_day in booking_days:
             tmp_date_today_str = b_day.date.strftime('%Y-%m-%d')             

             group_info[tmp_date_today_str] = dict(arrives=[v for v in vgroups if v['from_date'] == tmp_date_today_str], leaves=[v for v in vgroups if v['to_date'] == tmp_date_today_str], stays=[v for v in vgroups if v['to_date'] > tmp_date_today_str and v['from_date'] < tmp_date_today_str])

        return dict(booking_days=booking_days, group_info=group_info)
        
        
    @expose('hollyrosa.templates.booking_day_properties')
    @validate(validators={'id':validators.Int(not_empty=True)})
    #@require(Any(is_user('root'), has_permission('staff'), msg='Only staff members may change booking day properties'))
    def edit_booking_day(self,  id=None,  **kw):
        booking_day = holly_couch[id] #getBookingDay(id)
        tmpl_context.form = create_edit_booking_day_form
        return dict(booking_day=booking_day,  usage='edit')
        
    @validate(create_edit_booking_day_form, error_handler=edit_booking_day)      
    @expose()
    #@require(Any(is_user('root'), has_permission('staff'), msg='Only staff members may change booking day properties'))
    def save_booking_day_properties(self,  _id=None,  note='', num_program_crew_members=0,  num_fladan_crew_members=0):
        
        # important: if note is too big, dont try to store it in database because that will give all kinds of HTML rendering errors later
        #if len(note) > 1024:
        #    raise IOError, "note too big. I appologize for this improvised failure mode but we cannot allow this to propagate to the db"
        booking_day_c = holly_couch[_id]#getBookingDay(id)
        booking_day_c['note'] = note
        booking_day_c['num_program_crew_members'] = num_program_crew_members
        booking_day_c['num_fladan_crew_members'] = num_fladan_crew_members
        print 'HOLLY',_id
        holly_couch[_id]=booking_day_c
        
        raise redirect('/booking/day?day_id='+str(_id))
        

        
class BookingDay(BaseController):
    """
    The fallback controller for hollyrosa.
    
    By default, the final controller tried to fulfill the request
    when no other routes match. It may be used to display a template
    when all else fails, e.g.::
    
        def view(self, url):
            return render('/%s' % url)
    
    Or if you're using Mako and want to explicitly send a 404 (Not
    Found) response code when the requested template doesn't exist::
    
        import mako.exceptions
        
        def view(self, url):
            try:
                return render('/%s' % url)
            except mako.exceptions.TopLevelLookupException:
                abort(404)
    
    """
    
    
    def getAllDays(self):
        try:
            tmp = self._all_days
        except AttributeError:
            map_fun = '''function(doc) {
            if (doc.type == 'booking_day')
                emit(doc._id, doc.date);
            }'''
            all_days_c = holly_couch.query(map_fun) #DBSession.query(booking.BookingDay.id,  booking.BookingDay.date).all()
            self._all_days = [DataContainer(id=d.key,  date=d.value) for d in all_days_c]
            
            tmp = self._all_days
        
       
        return tmp
        
        
    
    def getAllActivityGroups(self):
        try:
            tmp = self._activity_groups
        except AttributeError:
            #self._activity_groups = DBSession.query(booking.ActivityGroup.id,  booking.ActivityGroup.title).all()
            map_fun = '''function(doc) {
            if (doc.type == 'activity_group')
                emit(doc._id, doc.title);
            }'''
            all_groups_c = holly_couch.query(map_fun) #DBSession.query(booking.BookingDay.id,  booking.BookingDay.date).all()
            self._activity_groups = [DataContainer(id=d.key,  title=d.value) for d in all_groups_c]
            
            tmp = self._activity_groups
        return tmp
        
        
    def getActivitySlotPositionsMap(self,  day_schema):
        """what do we map?"""
        try:
            tmp = self._activity_slot_position_map
        except AttributeError:
            self._activity_slot_position_map = day_schema['schema']
            tmp = self._activity_slot_position_map
            
        return tmp
        
    
    def fn_cmp_slot_row(self,  a,  b):
        return cmp(a.zorder,  b.zorder)
        
        
    def get_activities_map(self):
        map_fun = '''function(doc) {
        if (doc.type == 'activity')
        emit(doc._id, doc);
        }'''
        
        activities = holly_couch.query(map_fun)
        
        activities_map = dict()
        for a in activities:
            activities_map[a.key] = a.value
        return activities_map


    def make_slot_rows__of_day_schema(self,  day_schema,  activities_map):
        slot_row_schema = day_schema['schema']
        
        slot_rows = list()
        
        for tmp_activity_id, tmp_slots in slot_row_schema.items():
            tmp_activity = activities_map[tmp_activity_id]
            
            tmp_row = DataContainer(activity_id=tmp_activity_id,  zorder=tmp_slots[0]['zorder'] , title=tmp_activity['title'],  activity_group_id=tmp_activity['activity_group_id'],  bg_color=tmp_activity['bg_color'],  capacity=tmp_activity['capacity'],  slot_row_position=[ DataContainer(id=str(s['slot_id']),  time_from=s['time_from'],  time_to=s['time_to'],  duration=s['duration']) for s in tmp_slots[1:]])
            
            slot_rows.append(tmp_row)
        
        slot_rows.sort(self.fn_cmp_slot_row)
        return slot_rows


    def get_non_deleted_bookings_for_booking_day(self,  day_id):
        map_fun = """function(doc) {
        if (doc.type == 'booking') {
            if ((doc.booking_day_id == '""" + day_id+  """') && (doc.booking_state > -100)) {
                emit(doc._id, doc);
                }
            }
        }"""
        bookings_c = holly_couch.query(map_fun)
        
        bookings = dict()
        for x in bookings_c:
            b = x.value
            new_booking = DataContainer(id=b['_id'],  content=b['content'],  cache_content=b['cache_content'],  
                                        booking_state=b['booking_state'],  visiting_group_id=b['visiting_group_id'],  
                                        visiting_group_name=b['visiting_group_name'],  valid_from=b.get('valid_from', ''),  valid_to=b.get('valid_to', ''),  requested_date=b.get('requested_date', ''),  last_changed_by_id=b['last_changed_by_id'],  slot_id=b['slot_id'])
            ns = bookings.get(new_booking.slot_id, list())
            ns.append(new_booking)
            bookings[new_booking.slot_id] = ns
            
        return bookings
        
        
    def getSlotStateOfBookingDayIdAndSlotId(self,  booking_day_id,  slot_id):
        map_fun = """function(doc) {
        if (doc.type == 'slot_state') {
            if (doc.booking_day_id == '""" + booking_day_id+  """')  {
                if (doc.slot_id == '"""+slot_id+"""') {
                    emit(doc._id, doc);
                    }
                }
            }
        }"""
        
        slot_states = []
        for x in holly_couch.query(map_fun):
            b = x.value
            slot_states.append(b)
        return slot_states
        
        
    def get_slot_blockings_for_booking_day(self,  day_id):
        map_fun = """function(doc) {
        if (doc.type == 'slot_state') {
            if (doc.booking_day_id == '""" + day_id+  """')  {
                emit(doc._id, doc);
                }
            }
        }"""
        
        blockings_map = dict()
        for x in holly_couch.query(map_fun):
            b = x.value
            # fix replace hack later. slot_id. and slot. 
            blockings_map[b['slot_id']] = DataContainer(level=b['level'],  booking_day_id=b['booking_day_id'],  slot_id=b['slot_id'])
            
        return blockings_map
        
        
    def get_unscheduled_bookings_for_today(self,  date,  activity_map):
        map_fun = """function(doc) {
        if (doc.type == 'booking') {
            if (((doc.booking_day_id == '') && (doc.valid_to >= '""" + date +  """') && (doc.valid_from <= '""" + date +"""')  && (doc.booking_state > -100)) || ( (doc.booking_day_id == '') && (doc.valid_to == '') &&  (doc.booking_state > -100) ))  {
                emit(doc._id, doc);
                }
            }
        }"""
        
        unscheduled_bookings_c =  holly_couch.query(map_fun)
        unscheduled_bookings = list()
        for x in unscheduled_bookings_c:
            
            b = x.value
            a_id = b['activity_id']
            a = activity_map[a_id]
            
            new_booking = DataContainer(id=b['_id'],  content=b['content'],  cache_content=b['cache_content'],  
                                        booking_state=b['booking_state'],  visiting_group_id=b['visiting_group_id'],  
                                        visiting_group_name=b['visiting_group_name'],  valid_from=b['valid_from'],  valid_to=b['valid_to'],  requested_date=b['requested_date'],  last_changed_by_id=b['last_changed_by_id'],  slot_id=b['slot_id'],  activity_title=a['title'],  activity_group_id=a['activity_group_id'],  activity_id=a_id)
            unscheduled_bookings.append(new_booking)
        #DBSession.query(booking.Booking).options(eagerload('slot_row_position')).filter(or_(and_('booking_day_id is null',  'valid_to >= \'' +showing_sql_date + '\'',  'valid_from <= \''+showing_sql_date + '\'', 'booking_state > -100'), and_('booking_day_id is null',  'valid_to is null', 'booking_state > -100')  )).all()
        #print unscheduled_bookings
        return unscheduled_bookings
        
        
    def view(self, url):
        """Abort the request with a 404 HTTP status code."""
        abort(404)
        
        
    #@expose
    def getSumNumberOfRequiredCrewMembers(self,  slots,  slot_rows):
        """compute required number of program crew members, fladan crew members"""
        crew_count = dict()
        crew_count['program_count'] = 0
        crew_count['fladan_count'] = 0
        
        for x in slots:
            ac = x.slot_row_position.slot_row.activity
            if 4 == ac.activity_group_id:
                crew_count['fladan_count'] += ac.guides_per_slot
            else:
                crew_count['program_count'] += ac.guides_per_slot
        
        #...now we can also compute roughly the number of guids per slot row:
        for x in slot_rows:
            ac = x.activity
            if 4 == ac.activity_group_id:
                crew_count['fladan_count'] += ac.guides_per_day
            else:
                crew_count['program_count'] += ac.guides_per_day
                
        return crew_count
        
        
    @expose('hollyrosa.templates.booking_day')
    @validate(validators={'day_id':validators.Int(not_empty=False), 'day':validators.DateValidator(not_empty=False)})
    def day(self,  day=None,  day_id=None):
        """Show a complete booking day"""
        
        # TODO: we really need to get only the slot rows related to our booking day schema or things will go wrong at some point when we have more than one schema to work with.
        
        today_sql_date = datetime.datetime.today().date().strftime("%Y-%m-%d")
        activities_map = self.get_activities_map()
        
        if day_id != None:
            booking_day_o = holly_couch[day_id]
            
            
        elif day=='today':
            
            #...we need to get all slots for 'today'
            #requested_date = datetime.datetime.today().date()
            booking_day_o = bookingDayOfDate(today_sql_date)
            #booking_day_o = getBookingDayOfDate(str(today_sql_date)) #DBSession.query(booking.BookingDay).filter('date=\''+today_sql_date+'\'').one()
            day_id = booking_day_o['_id']
            
        else: # we're guessing day is a date options(eagerload_all('')).
            booking_day_o = getBookingDayOfDate(str(day)) #DBSession.query(booking.BookingDay).filter('date=\''+str(day)+'\'').one()
            day_id = booking_day_o['_id']
        
        booking_day_o['id'] = day_id
        day_schema_id = booking_day_o['day_schema_id']
        day_schema = holly_couch[day_schema_id]
        slot_rows = self.make_slot_rows__of_day_schema(day_schema,  activities_map)
            
        #...first, get booking_day for today
        new_bookings = self.get_non_deleted_bookings_for_booking_day(day_id)
        
        #...we need a mapping from activity to a list / tupple slot_row_position
        #
        #   the new version should be a list of rows. Each row is either a DataContainer or a dict (basically the same...)
        #    We need to know activity name, color, id and group (which we get from the activities) and we need a list of slot positions
        activity_slot_position_map = self.getActivitySlotPositionsMap(day_schema) 
        
        #...find all unscheduled bookings
        showing_sql_date = str(booking_day_o['date']) #.strftime("%Y-%m-%d")
        unscheduled_bookings = self.get_unscheduled_bookings_for_today(showing_sql_date,  activities_map)
        
        #...compute all blockings, create a dict mapping slot_row_position_id to actual state
        blockings_map = self.get_slot_blockings_for_booking_day(day_id)
        days = self.getAllDays()
        activity_groups = self.getAllActivityGroups() 
            
        return dict(booking_day=booking_day_o,  slot_rows=slot_rows,  bookings=new_bookings,  unscheduled_bookings=unscheduled_bookings,  activity_slot_position_map=activity_slot_position_map,  blockings_map=blockings_map,  workflow_map=workflow_map,  days=days,  getRenderContent=getRenderContent,  activity_groups=activity_groups)
        
        
    @expose('hollyrosa.templates.booking_day_fladan')
    @validate(validators={'day_id':validators.Int(not_empty=False), 'day':validators.DateValidator(not_empty=False), 'ag':validators.String(not_empty=False)})
    def fladan_day(self,  day=None,  day_id=None, ag=''):
        """Show a complete booking day"""
        
        workflow_img_mapping = {}
        workflow_img_mapping['0'] = 'sheep.png'
        workflow_img_mapping['10'] = 'paper_to_sign.png'
        workflow_img_mapping['20'] = 'check_mark.png'
        workflow_img_mapping['-10'] = 'alert.png'
        workflow_img_mapping['-100'] = 'alert.png'
        workflow_img_mapping['unscheduled'] = 'alert.png'
        

        slot_rows=DBSession.query(booking.SlotRow).options(eagerload('activity'))
        slot_rows_n = []
        for s in slot_rows:
            if (s.activity.activity_group.title == ag) or (ag == ''):
                slot_rows_n.append(s)

        today_sql_date = datetime.datetime.today().date().strftime("%Y-%m-%d")
        if day_id != None:
            booking_day_o = DBSession.query(booking.BookingDay).filter('id='+str(day_id)).one()
                
        else: # we're guessing day is a date
            booking_day_o = DBSession.query(booking.BookingDay).filter('date=\''+str(day)+'\'').one()
        
        #...first, get booking_day for today
        bookings = DBSession.query(booking.Booking).filter('booking_day_id='+str(booking_day_o.id)).all()
        
        new_bookings = dict()
        for s in bookings:
            if (s.activity.activity_group.title == ag) or (ag == ''):
                ns = new_bookings.get(s.slot_row_position_id, list())
                ns.append(s)
                new_bookings[s.slot_row_position_id] = ns
            
        
        
        #...we need a mapping from activity to a list / tupple slot_row_position
        activity_slot_position_map = dict()
        for slr in slot_rows:
            activity_slot_position_map[slr.activity_id] = [slrp for slrp in slr.slot_row_position]
        
        #...compute all blockings, create a dict mapping slot_row_position_id to actual state
        blockings = DBSession.query(booking.SlotRowPositionState).filter('booking_day_id='+str(booking_day_o.id)).all()
        blockings_map = dict()
        for b in blockings:
            blockings_map[b.slot_row_position_id] = b
            
        #days = DBSession.query(booking.BookingDay.id,  booking.BookingDay.date).all()
        
        #raise IOError,  new_bookings
            
        return dict(booking_day=booking_day_o,  slot_rows=slot_rows_n,  bookings=new_bookings,  activity_slot_position_map=activity_slot_position_map,  blockings_map=blockings_map,  workflow_map=workflow_map, activity_group=ag,  workflow_img_mapping=workflow_img_mapping)



        
    @expose()
    #@require(Any(is_user('root'), has_permission('pl'), msg='Only PL may delete a booking request'))
    @validate(validators={'booking_day_id':validators.Int(not_empty=True), 'booking_id':validators.Int(not_empty=True)})
    def delete_booking(self,  booking_day_id,  booking_id):
        ###booking_o = DBSession.query(booking.Booking).filter('id='+str(booking_id)).one()        
        ###tmp_activity = booking_o.activity
        
        ###remember_delete_booking_request(booking_o, changed_by='')
        # cant do any more, foreign key problem: DBSession.delete(booking_o)
        tmp_booking = holly_couch[booking_id]
        tmp_activity_id = tmp_booking['activity_id']
        deleteBooking(tmp_booking)

        raise redirect('/booking/day?day_id='+str(booking_day_id) + make_booking_day_activity_anchor(tmp_activity_id)) 
        

    @validate(create_validate_unschedule_booking)
    @expose()
    #@require(Any(is_user('root'), has_permission('staff'), msg='Only staff members may unschedule booking request'))
    def unschedule_booking(self,  booking_day_id,  booking_id):
        b = holly_couch[booking_id] #DBSession.query(booking.Booking).filter('id='+booking_id).one()
        b['last_changed_by_id'] = getLoggedInUser(request).user_id
        
        #####remember_unschedule_booking(booking=b, slot_row_position=b.slot_row_position, booking_day=b.booking_day,  changed_by='')

        b['booking_state'] = 0
        b['booking_day_id'] = ''
        b['slot_id'] = ''
        holly_couch[b['_id']] = b
        raise redirect('day?day_id='+booking_day_id + make_booking_day_activity_anchor(b['activity_id']))
        
    @validate(create_validate_schedule_booking)
    @expose()
    #@require(Any(is_user('root'), has_permission('staff'), msg='Only staff members may schedule booking request'))
    def schedule_booking(self,  booking_day_id,  booking_id,  slot_row_position_id):
        b = holly_couch[booking_id] 
        b['last_changed_by_id'] = getLoggedInUser(request).user_id
        ####remember_schedule_booking(booking=b, slot_row_position=DBSession.query(booking.SlotRowPosition).filter('id='+slot_row_position_id).one(), booking_day=DBSession.query(booking.BookingDay).filter('id='+booking_day_id).one(),  changed_by='')
        
        b['booking_day_id'] = booking_day_id
        b['slot_id'] = slot_row_position_id
        holly_couch[b['_id']] = b
        raise redirect('day?day_id='+booking_day_id + make_booking_day_activity_anchor(b['activity_id']))
        
        
    @expose('hollyrosa.templates.edit_booked_booking')
    @validate(validators={'booking_day_id':validators.Int(not_empty=True), 'slot_position_id':validators.Int(not_empty=True)})
    @require(Any(is_user('root'), has_permission('staff'), msg='Only staff members may book a slot'))
    def book_slot(self,  booking_day_id=None,  slot_position_id=None):
        tmpl_context.form = create_edit_book_slot_form
         
        #...find booking day and booking row
        booking_day = getBookingDay(str(booking_day_id))
        #slot_position = DBSession.query(booking.SlotRowPosition).filter('id='+str(slot_position_id)).one() 
        
        
        tmp_visiting_groups = get_visiting_groups_at_date(booking_day['date']) #DBSession.query(booking.VisitingGroup.id, booking.VisitingGroup.name,  booking.VisitingGroup.todate,  booking.VisitingGroup.fromdate ).filter(and_('visiting_group.fromdate <= \''+str(booking_day.date) + '\'', 'visiting_group.todate >= \''+str(booking_day.date) + '\''   )   ).all()
        visiting_groups = [(e['_id'],  e['name']) for e in tmp_visiting_groups] 
        
        #...find out activity of slot_id for booking_day
        schema = holly_couch[booking_day['day_schema_id']]
        
        activity_id = None
        for tmp_activity_id,  tmp_slot_row in schema['schema'].items():
            for tmp_slot in tmp_slot_row[1:]:
                if tmp_slot['slot_id'] == slot_position_id:
                    activity_id = tmp_activity_id
                    slot = tmp_slot
                    break
        
        activity = holly_couch[activity_id] #  #DBSession.query(booking.Activity).filter('id='+str(slot_position.slot_row.activity.id)).one()
        booking_o = DataContainer(content='', visiting_group_name='',  valid_from=None,  valid_to=None,  requested_date=None,  return_to_day_id=booking_day_id,  activity_id=activity_id, id=None,  activity=activity,  booking_day_id=booking_day_id,  slot_row_position_id=slot_position_id)
        
        return dict(booking_day=booking_day,    booking=booking_o,  visiting_groups=visiting_groups, edit_this_visiting_group=0,  slot_position=slot)
        

    @expose('hollyrosa.templates.show_booking')
    @validate(validators={'id':validators.Int(not_empty=True), 'return_to_day_id':validators.Int(not_empty=False)})
    def view_booked_booking(self,  return_to_day_id=None,  id=None):
       
        #...find booking day and booking row
        booking_o = holly_couch[id] 
        booking_o.return_to_day_id = return_to_day_id
        activity_id = booking_o['activity_id']
        
        booking_day_id = None
        booking_day = None
        slot_position = None
        
        if booking_o.has_key('booking_day_id'):
            booking_day_id = booking_o['booking_day_id']
            if '' != booking_day_id:
                booking_day = holly_couch[booking_day_id] #booking_o.booking_day
            
            
            
                #REFACTOR OUT
                tmp_day_schema = holly_couch[booking_day['day_schema_id']] 
                tmp_schema = tmp_day_schema['schema'] 
    
                #...we know the slot position: booking_o['slot_id'] we just need to find it in the schema.
                
                if booking_o.has_key('slot_id'):
                    slot_id = booking_o['slot_id']
                    if ''!=slot_id:
                        for tmp_row in tmp_schema.values():
                            print tmp_row
                            for tmp_slot in tmp_row[1:]:
                                if tmp_slot['slot_id'] == slot_id:
                                    slot_position = tmp_slot
                                    break
        
        activity = holly_couch[activity_id] 
        history = getBookingHistory(id)
        #history.reverse()
        return dict(booking_day=booking_day,  slot_position=slot_position, booking=booking_o,  workflow_map=workflow_map,  history=history,  change_op_map=change_op_map,  getRenderContent=getRenderContentDict,  activity=activity)
        
        
    @expose('hollyrosa.templates.edit_booked_booking')
    @validate(validators={'id':validators.UnicodeString(not_empty=True), 'return_to_day':validators.UnicodeString(not_empty=False)})
    @require(Any(is_user('root'), has_permission('staff'), msg='Only staff members may change booked booking properties'))
    def edit_booked_booking(self,  return_to_day_id=None,  id=None,  **kw):
        tmpl_context.form = create_edit_book_slot_form
        print 'ID',  str(return_to_day_id)
        
        #...find booking day and booking row
        booking_o = holly_couch[id] 
        booking_o['return_to_day_id'] = return_to_day_id
        
        booking_day_id = booking_o['booking_day_id']
        booking_day = holly_couch[booking_day_id]
        slot_id = booking_o['slot_id']
        
        #REFACTOR OUT
        tmp_day_schema = holly_couch[booking_day['day_schema_id']] 
        tmp_schema = tmp_day_schema['schema'] 
    
        #...we know the slot position: booking_o['slot_id'] we just need to find it in the schema.
        slot_id = booking_o['slot_id']
        for tmp_row in tmp_schema.values():
            print tmp_row
            for tmp_slot in tmp_row[1:]:
                if tmp_slot['slot_id'] == slot_id:
                    slot_position = tmp_slot
        #...refactor - make booking from booking_couch transfering to DataContainer
        activity_id = booking_o['activity_id']
        activity = holly_couch[activity_id]
        booking_ = DataContainer(activity_id=activity_id, activity=activity,  id=booking_o['_id'],  visiting_group_name=booking_o['visiting_group_name'],  visiting_group_id=booking_o['visiting_group_id'],  content=booking_o['content'], return_to_day_id=return_to_day_id )
        
        tmp_visiting_groups = get_visiting_groups_at_date(booking_day['date']) #DBSession.query(booking.VisitingGroup.id, booking.VisitingGroup.name,  booking.VisitingGroup.todate,  booking.VisitingGroup.fromdate ).filter(and_('visiting_group.fromdate <= \''+str(booking_day.date) + '\'', 'visiting_group.todate >= \''+str(booking_day.date) + '\''   )   ).all()
        visiting_groups = [(e['_id'],  e['name']) for e in tmp_visiting_groups]  # REFACTOR
        
 
        
        return dict(booking_day=booking_day,  slot_position=slot_position, booking=booking_,  visiting_groups=visiting_groups, edit_this_visiting_group=booking_o['visiting_group_id'],  activity=activity)
        
        
    @validate(create_edit_book_slot_form, error_handler=edit_booked_booking)      
    @expose()
    @require(Any(is_user('root'), has_permission('staff'), msg='Only staff members may change booked booking properties'))
    def save_booked_booking_properties(self,  id=None,  content=None,  visiting_group_name=None,  visiting_group_id=None,  activity_id=None,  return_to_day_id=None, slot_row_position_id=None,  booking_day_id=None,  block_after_book=False ):
       
        #...id can be None if a new slot is booked
        if None == id or '' == id:
            is_new = True
            old_booking = dict(type='booking',  valid_from='',  valid_to='',  requested_date='')#booking.Booking()
            old_booking['slot_id'] = slot_row_position_id
            old_booking['booking_day_id'] = booking_day_id
        else:
            is_new = False
            old_booking = holly_couch[id]
        
        old_visiting_group_name = old_booking.get('visiting_group_name', '')
        old_booking['visiting_group_name'] = visiting_group_name
        old_booking['visiting_group_id'] = visiting_group_id
        old_booking['last_changed_by_id'] = getLoggedInUser(request).user_id
        
        old_booking['content'] = content
        
        old_booking['cache_content'] = computeCacheContent(holly_couch, content, visiting_group_id)
        
            
        #...make sure activity is set
        if (None != activity_id) or (''==activity_id):
            tmp_activity_id = activity_id
            old_booking['activity_id'] = activity_id
        else:
            old_booking['activity'] = old_booking['slot_id'].activity_id # again we need to lookup activity
            tmp_activity_id = None
            
        activity = holly_couch[tmp_activity_id]
        
        #...again we need to look up activity
        old_booking['booking_state'] = activity['default_booking_state']
        
        if is_new:
            #remember_book_slot(booking=old_booking, slot_row_position=DBSession.query(booking.SlotRowPosition).filter('id='+str(slot_row_position_id)).one(), booking_day=DBSession.query(booking.BookingDay).filter('id='+str(booking_day_id)).one(),  changed_by='')
            #DBSession.add(old_booking)
            holly_couch['booking.'+genUID()] = old_booking
        else:
            #remember_booking_properties_change(booking=old_booking, slot_row_position=old_booking.slot_row_position, booking_day=old_booking.booking_day,  old_visiting_group_name=old_visiting_group_name,  new_visiting_group_name=visiting_group_name, new_content='', changed_by='')
            
            holly_couch[old_booking['_id']] = old_booking
        
        #...block after book?
        if block_after_book:
            self.block_slot_helper(booking_day_id,  slot_row_position_id)
        
        raise redirect('day?day_id='+str(return_to_day_id) + make_booking_day_activity_anchor(tmp_activity_id))
    
        
    @expose('hollyrosa.templates.view_activity')
    @validate(validators={'activity_id':validators.Int(not_empty=True)})
    def view_activity(self,  activity_id=None):
        return dict(activity=holly_couch[activity_id])
        
    
    @expose('hollyrosa.templates.edit_activity')
    @validate(validators={'activity_id':validators.Int(not_empty=True)})
    @require(Any(is_user('root'), has_permission('staff'), msg='Only staff members may change activity information'))
    def edit_activity(self, activity_id=None,  **kw):
        tmpl_context.form = create_edit_activity_form
        activity_groups = self.get_activity_groups() #DBSession.query(booking.ActivityGroup.id, booking.ActivityGroup.title).all() # in the future filter on from and to dates
        if None == activity_id:
            activity = DataContainer(id=None,  title='',  info='')
        elif id=='':
            activity = DataContainer(id=None,  title='', info='')
        else:
            activity = holly_couch[activity_id] #DBSession.query(booking.Activity).filter('id=' + str(activity_id)).one()
        return dict(activity=activity,  activity_group=activity_groups,  activity_groups=activity_groups)
        
        
    @validate(create_edit_activity_form, error_handler=edit_activity)      
    @expose()
    @require(Any(is_user('root'), has_permission('staff'), msg='Only staff members may change activity properties'))
    def save_activity_properties(self,  id=None,  title=None,  external_link='', internal_link='',  print_on_demand_link='',  description='', tags='', capacity=0,  default_booking_state=0,  activity_group_id=1,  gps_lat=0,  gps_long=0,  equipment_needed=False, education_needed=False,  certificate_needed=False,  bg_color='', guides_per_slot=0,  guides_per_day=0 ):
        if None == id:
            acticity = booking.Activity()
            is_new = True
            raise IOError,  "None!!!"
        else:
            activity = DBSession.query(booking.Activity).filter('id='+ str(id)).one()
            is_new= False
            
        activity.title = title
        activity.description= description
        activity.external_link = external_link
        activity.internal_link = internal_link
        activity.print_on_demand_link = print_on_demand_link
        activity.tags=tags
        activity.capacity=capacity
#        #activity.default_booking_state=default_booking_state
        activity.activity_group_id = activity_group_id
#        activity.gps_lat = gps_lat
 #       activity.gps_long = gps_long
        activity.equipment_needed = equipment_needed
        activity.education_needed = education_needed
        activity.certificate_needed = certificate_needed
        activity.bg_color = bg_color
        activity.guides_per_slot = guides_per_slot
        activity.guides_per_day = guides_per_day
            
        if is_new:
            DBSession.add(activity)
        raise redirect('/booking/view_activity',  activity_id=id)
     
    def fnSortOnThirdItem(self, a , b):
        return cmp(a[2], b[2])
        
        
    @expose('hollyrosa.templates.request_new_booking')
    @validate(validators={'booking_day_id':validators.UnicodeString(not_empty=True), 'id':validators.UnicodeString(not_empty=False), 'visiting_group_id':validators.UnicodeString(not_empty=False)})
    #@require(Any(is_user('root'), has_permission('staff'), msg='Only staff members may change a booking'))
    def edit_booking(self,  booking_day_id=None,  id=None, visiting_group_id='', **kw):
        tmpl_context.form = create_edit_new_booking_request_form
        
        # We still need to add some reasonable sorting on the activities abd the visiting groups
        
        activities_tmp = self.get_activities_map() #DBSession.query(booking.Activity.id, booking.Activity.title).all()
        activities = [(e['_id'],  e['title'],  e.get('zorder', '')) for e in activities_tmp.values()] 
        activities.sort(self.fnSortOnThirdItem)
        tmp_visiting_groups = get_visiting_groups() 
        visiting_groups = [(e['_id'],  e['name']) for e in tmp_visiting_groups] 
        
        tmp_visiting_group = holly_couch[visiting_group_id]
        
        #...patch since this is the way we will be called if validator for new will fail
        if (visiting_group_id != '') and (visiting_group_id != None):
            booking_o = DataContainer(id='', content='', visiting_group_id = visiting_group_id, visiting_group_name=tmp_visiting_group['name'])
        elif id=='' or id==None:
            booking_o = DataContainer(id='', content='')
        else:
            booking_o = holly_couch[id] #DBSession.query(booking.Booking).filter('id='+str(id)).one()
        booking_o.return_to_day_id = booking_day_id
        return dict(visiting_groups=visiting_groups,  activities=activities, booking=booking_o)
        
        
    @expose('hollyrosa.templates.move_booking')
    @require(Any(is_user('root'), has_permission('staff'), msg='Only staff members may change a booking'))
    @validate(validators={'return_to_day_id':validators.UnicodeString(not_empty=False), 'id':validators.UnicodeString(not_empty=False)})
    def move_booking(self,  return_to_day_id=None,  id=None,  **kw):
        tmpl_context.form = create_move_booking_form
        activities_tmp = self.get_activities_map() #DBSession.query(booking.Activity.id, booking.Activity.title).all()
        activities = [(e['_id'],  e['title'],  e.get('zorder', '')) for e in activities_tmp.values()] 
        
        #...patch since this is the way we will be called if validator for new will fail
        booking_o = holly_couch[id] #DBSession.query(booking.Booking).filter('id='+str(id)).one()
        booking_o.return_to_day_id = return_to_day_id
        activity_id,  slot_o = getSlotAndActivityIdOfBooking(booking_o)
        activity_o = holly_couch[booking_o['activity_id']]
        booking_day = holly_couch[booking_o['booking_day_id']]
        booking_ = DataContainer(activity_id=activity_id,  content=booking_o['content'],  cache_content=booking_o['cache_content'],  visiting_group_name=booking_o['visiting_group_name'],  id=booking_o['_id'],  return_to_day_id=return_to_day_id)
        return dict(activities=activities, booking=booking_,  activity=activity_o,  booking_day=booking_day,  slot=slot_o,  getRenderContent=getRenderContent)
        
        
    @validate(create_move_booking_form, error_handler=move_booking)      
    @expose()
    @require(Any(is_user('root'), has_permission('staff'), msg='Only staff members may change activity properties'))
    def save_move_booking(self,  id=None,  activity_id=None,  return_to_day_id=None,  **kw):
        new_booking = holly_couch[id] 
        print 'id',id,'new', new_booking.items()
        
        #...slot row position must be changed, so we need to find slot row of activity and then slot row position with aproximately the same time span
        old_slot_id = new_booking['slot_id']
        #old_activity_id,  old_slot = getSlotAndActivityIdOfBooking(new_booking)
        booking_day_id = new_booking['booking_day_id']
        booking_day_o = holly_couch[booking_day_id]
        schema_o = holly_couch[booking_day_o['day_schema_id']]
        
        #...iterate thrue the schema first time looking for slot_id_position and activity
        the_schema = schema_o['schema']
        for tmp_activity_id,  tmp_activity_row in the_schema.items():
            tmp_slot_index = 1
            for tmp_slot in tmp_activity_row[1:]:
                if tmp_slot['slot_id'] == old_slot_id:
                    old_activity_id = tmp_activity_id
                    old_slot = tmp_slot
                    old_slot_index = tmp_slot_index
                    break
                tmp_slot_index += 1
        
        tmp_new_slot_row = the_schema[activity_id]
        new_slot = tmp_new_slot_row[old_slot_index]
        new_slot_id = new_slot['slot_id']
        #new_slot_row = DBSession.query(booking.SlotRow).filter('activity_id='+str(activity_id)).one()
        #for tmp_slot_row_position in new_slot_row.slot_row_position:
         #   
         #   # TODO: too hackish below
         #   if tmp_slot_row_position.time_from == old_slot_row_position.time_from:
         #       new_booking.slot_row_position = tmp_slot_row_position
        
        #...it's not perfectly normalized that we also need to change activity id
        new_booking['activity_id'] = activity_id
        new_booking['slot_id'] = new_slot_id
        holly_couch[new_booking['_id']] = new_booking
        
        raise redirect('/booking/day?day_id='+str(return_to_day_id)) 
        
        
    @validate(create_edit_new_booking_request_form, error_handler=edit_booking)   
    @expose()
    def save_new_booking_request(self, content='',  activity_id=None,  visiting_group_name='',  visiting_group_select=None,  valid_from=None,  valid_to=None,  requested_date=None,  visiting_group_id=None,  id=None,  return_to_day_id=None):
        is_new=False
        if id ==None or id=='':
            new_booking = dict(type='booking',  booking_day_id='', slot_id='') #booking.Booking()
            is_new = True
        else:
            new_booking = holly_couch[id] #DBSession.query(booking.Booking).filter('id='+str(id)).one()
            old_booking = DataContainer(activity=new_booking.activity,  visiting_group_name=new_booking.visiting_group_name,  valid_from=new_booking.valid_from,  valid_to=new_booking.valid_to,  requested_date=new_booking.requested_date,  content=new_booking.content,  id=new_booking.id)
            
        if is_new:
            print 'setting booking state=0'
            new_booking['booking_state'] = 0
        else:
           # DEPENDS ON WHAT HAS CHANGED. Maybe content change isnt enough to change state?
           new_booking['booking_state'] = 0
            
        new_booking['content'] = content
        
        ##vgroup = DBSession.query(booking.VisitingGroup).filter('id='+str(visiting_group_id)).one()
        new_booking['visiting_group_id'] = visiting_group_id
        print 'compute cache content'
        new_booking['cache_content'] = computeCacheContent(holly_couch, content, visiting_group_id)
        
        
        new_booking['activity_id'] = activity_id
        new_booking['visiting_group_name'] = visiting_group_name
        new_booking['last_changed_by_id'] = getLoggedInUser(request).user_id
        

        #...todo add dates, but only after form validation
        new_booking['requested_date'] = str(requested_date)
        new_booking['valid_from'] = str(valid_from)
        new_booking['valid_to'] = str(valid_to)
        #new_booking['timestamp'] = 
        #raise IOError,  "%s %s %s" % (str(requested_date),  str(valid_from),  str(valid_to))
        print 'saving to db'
        if is_new:
            holly_couch['booking.'+genUID()] = new_booking
            #####remember_new_booking_request(new_booking)
        else:
            pass
            #####remember_booking_request_change(old_booking=old_booking,  new_booking=new_booking)
        
        if return_to_day_id != None:
            if return_to_day_id != '':
                raise redirect('/booking/day?day_id='+str(return_to_day_id)) 
        if is_new:
            raise redirect('/visiting_group/view_all#vgroupid_'+str(visiting_group_id))
        raise redirect('/calendar/overview')
        
    
    @expose()
    @validate(validators={'id':validators.UnicodeString(not_empty=True)})
    @require(Any(is_user('root'), has_permission('pl'), msg='Only PL can block or unblock slots'))
    def prolong(self,  id):
        # TODO: one of the problems with prolong that just must be sloved is what do we do if the day shema is different for the day after?
        
        #...first, find the slot to prolong to
        old_booking = holly_couch[id] # move into model
        booking_day_id = old_booking['booking_day_id']
        booking_day = holly_couch[booking_day_id]
        day_schema_id = booking_day['day_schema_id']
        day_schema = holly_couch[day_schema_id]
        old_slot_id = old_booking['slot_id']
        schema = day_schema['schema']

        #... TODO: find the slot and slot index. FACTOR OUT COMPARE MOVE BOOKING
        for tmp_activity_id,  tmp_activity_row in schema.items():
            tmp_slot_index = 1
            for tmp_slot in tmp_activity_row[1:]:
                if tmp_slot['slot_id'] == old_slot_id:
                    old_activity_id = tmp_activity_id
                    old_slot = tmp_slot
                    old_slot_index = tmp_slot_index
                    old_slot_row = tmp_activity_row
                    break
                tmp_slot_index += 1
        
        activity = holly_couch[old_activity_id]
        
        if (old_slot_index+1) >= len(old_slot_row):
            flash('last slot')
            
            new_booking_day_id = getNextBookingDayId(booking_day)
            #new_booking_slot_row_position_id = slot_row_positions[0].id
            new_slot_id = old_slot_row[1]['slot_id']
        else:
            
#            i = 0
#            last_slrp = None
#            for slrp in slot_row_positions:
#                if last_slrp ==  old_booking.slot_row_position_id:
#                    break
#                last_slrp = slrp.id 
#            new_booking_slot_row_position_id = slrp.id
            new_slot_id = old_slot_row[old_slot_index+1]['slot_id']
            new_booking_day_id = booking_day_id
        
        #...then figure out if the slot to prolong to is blocked
        
        #todo: figure out if slot is blocked
        
        #new_booking_slot_row_position_state = DBSession.query(booking.SlotRowPositionState).filter(and_('slot_row_position_id='+str(new_booking_slot_row_position_id), 'booking_day_id='+str(new_booking_booking_day_id))) .all()
        new_booking_slot_row_position_states = self.getSlotStateOfBookingDayIdAndSlotId(new_booking_day_id,  new_slot_id)
        
        #...if it isn't blocked, then book that slot.
        if len(new_booking_slot_row_position_states) == 0:

            #...find the booking
        
            new_booking = dict(type='booking')
            for k, v in old_booking.items():
                new_booking[k] = v
            
            new_booking['last_changed_by_id'] = getLoggedInUser(request).user_id
            new_booking['slot_id'] = new_slot_id
            new_booking['booking_day_id'] = new_booking_day_id
                               
                               #content=old_booking['content'],  cache_content=old_booking['cache_content'], activity_id=old_booking['activity_id'],  visiting_group_name=old_booking['visiting_group_name'] , 
                              # =, visiting_group_id=old_booking['visiting_group_id'] ,  requested_date=old_booking.get()['requested_date'], valid_from=old_booking['valid_from'], 
                             #  valid_to=old_booking['valid_to'] , booking_day_id=new_booking_day_id,  slot_id=new_slot_id )
            new_booking['booking_state'] = activity['default_booking_state']
            
            
            holly_couch['booking.'+genUID()] = new_booking
            #remember_new_booking_request(new_booking)
        else:
            flash('wont prolong since next slot is blocked',  'warning')
            redirect('/booking/day?day_id='+str(booking_day_id)) 
            
        raise redirect('/booking/day?day_id='+str(new_booking['booking_day_id']) + make_booking_day_activity_anchor(new_booking['activity_id'])) 


    def getActivityIdOfBooking(self,  booking_day_id,  slot_id):
        """
        try to find activity given booking day and slot_id
        
        We need to find booking day, then schema, in schema there are rows per activity. Somewhere in that schema is the answear.
        """
        booking_o = holly_couch[booking_day_id]
        schema_o = holly_couch[booking_o['day_schema_id']]
        
        #...iterate thrue the schema
        for tmp_activity_id,  tmp_activity_row in schema_o['schema'].items():
            for tmp_slot in tmp_activity_row[1:]:
                if tmp_slot['slot_id'] == slot_id:
                    return tmp_activity_id
                    
        # todo: I dont think it is unreasonable that each schema has a lookuptable slot_id -> activity that is updated if the schema is updated.
        

    def block_slot_helper(self, booking_day_id,  slot_id,  level = 1):
        ##slot_row_position_state = booking.SlotRowPositionState()
        ##slot_row_position_state.slot_row_position_id = slot_row_position_id
        ##slot_row_position_state.booking_day_id = booking_day_id
        ##slot_row_position_state.level = int(level)
        slot_state = dict(slot_id=slot_id,  booking_day_id=booking_day_id, level=level,  type='slot_state')
        holly_couch['slot_state.'+genUID()] = slot_state #DBSession.add(slot_row_position_state)
        # todo: set state variable when it has been introduced
        ####slot_row_position = DBSession.query(booking.SlotRowPosition).filter('id='+str(slot_row_position_id)).one()
        #### todo: remember_block_slot(slot_row_position=slot_row_position, booking_day=DBSession.query(booking.BookingDay).filter('id='+str(booking_day_id)).one(),  level=level,  changed_by='')
        
        
    @expose()
    @validate(validators={'booking_day_id':validators.Int(not_empty=True), 'slot_row_position_id':validators.Int(not_empty=True), 'level':validators.Int(not_empty=True)})
    #@require(Any(is_user('root'), has_permission('pl'), msg='Only PL can block or unblock slots'))
    def block_slot(self, booking_day_id,  slot_row_position_id,  level = 1):
        self.block_slot_helper(booking_day_id, slot_row_position_id, level=level)
        activity_id = self.getActivityIdOfBooking(booking_day_id,  slot_row_position_id)
        raise redirect('day?day_id='+booking_day_id + make_booking_day_activity_anchor(activity_id))
        

    @expose()
    @validate(validators={'booking_day_id':validators.Int(not_empty=True), 'slot_row_position_id':validators.Int(not_empty=True)})
    #@require(Any(is_user('root'), has_permission('pl'), msg='Only PL can block or unblock slots'))
    def unblock_slot(self, booking_day_id,  slot_row_position_id):
        #### todo: reintroduced    remember_unblock_slot(slot_row_position=slot_row_position_state.slot_row_position, booking_day=slot_row_position_state.booking_day,  changed_by='',  level=slot_row_position_state.level)

        # todo: set state variable when it has been introduced
        tmp_slot_states = self.getSlotStateOfBookingDayIdAndSlotId( booking_day_id,  slot_row_position_id)
        for sl in tmp_slot_states:
            holly_couch.delete(sl)
        activity_id = self.getActivityIdOfBooking(booking_day_id,  slot_row_position_id)
        raise redirect('day?day_id='+str(booking_day_id) + make_booking_day_activity_anchor(activity_id)) 
        

    @expose('hollyrosa.templates.edit_multi_book')
    @validate(validators={'booking_id':validators.Int(not_empty=True)})
    @require(Any(is_user('root'), has_permission('staff'), msg='Only staff members may use multibook functionality'))
    def multi_book(self,  booking_id=None,  **kw):
        booking_o = holly_couch[booking_id] #DBSession.query(booking.Booking).filter('id='+str(booking_id)).one()
        booking_days = DBSession.query(booking.BookingDay).all()
        slot_row = DBSession.query(booking.SlotRow).filter('activity_id='+str(booking_o.activity.id)).one()
        
        
        bookings = {}
        
        for tmp_booking_day in booking_days:
            bookings[tmp_booking_day.id] = {}
        
        for tmp_slot_row_position in slot_row.slot_row_position:
            bookings_of_slot_position = DBSession.query(booking.Booking).filter('slot_row_position_id='+str(tmp_slot_row_position.id)).all()
            
            for tmp_booking in bookings_of_slot_position:
                if None == tmp_slot_row_position.id:
                    raise IOError,  "None not expected"
                if None == tmp_booking.id:
                    raise IOError,  "None not expected"
                    
                if not bookings[tmp_booking.booking_day_id].has_key(tmp_slot_row_position.id):
                    bookings[tmp_booking.booking_day_id][tmp_slot_row_position.id] = []
                bookings[tmp_booking.booking_day_id][tmp_slot_row_position.id].append(tmp_booking)
        
        slot_row_position = booking_o.slot_row_position
        slot_row = slot_row_position.slot_row
        slot_row_id = slot_row.id
        
        blockings = DBSession.query(booking.SlotRowPositionState).join(booking.SlotRowPosition).filter('slot_row_position.slot_row_id='+str(slot_row_id)).all()
        blockings_map = dict()
        for b in blockings:
            tmp_booking_day_id = b.booking_day_id
            blockings_map[str(tmp_booking_day_id)+':'''+ str(b.slot_row_position_id)] = b
            
        return dict(booking=booking_o,  booking_days=booking_days,  booking_day=None,  slot_row=slot_row,  blockings_map=blockings_map,  bookings=bookings,  getRenderContent=getRenderContent)  

        
    @expose("json")
    @validate(validators={'booking_day_id':validators.Int(not_empty=True), 'slot_row_position_id':validators.Int(not_empty=True), 'activity_id':validators.Int(not_empty=True), 'content':validators.UnicodeString(not_empty=False), 'visiting_group_id_id':validators.Int(not_empty=True), 'block_after_book':validators.Bool(not_empty=False)})
    @require(Any(is_user('root'), has_permission('staff'), msg='Only staff members may change booked booking properties'))
    def create_booking_async(self,  booking_day_id=0,  slot_row_position_id=0,  activity_id=0,  content='', block_after_book=False,  visiting_group_id=None):
                
        #...TODO refactor to isBlocked
        slot_row_position_state = DBSession.query(booking.SlotRowPositionState).filter(and_('booking_day_id='+booking_day_id, 'slot_row_position_id='+slot_row_position_id)).first()
        
        if None != slot_row_position_state:
            return dict(error_msg="slot blocked, wont book")
            
        else:
            new_booking = booking.Booking()
            new_booking.booking_state = 0
            new_booking.content = content
            
            #...render cache content
            
            
            
            vgroup = DBSession.query(booking.VisitingGroup).filter('visiting_group.id='+visiting_group_id).one()
            
            new_booking.cache_content = computeCacheContent(DBSession, content, visiting_group_id)
            
            
            
            new_booking.activity_id = activity_id
            
            new_booking.last_changed_by_id = getLoggedInUser(request).user_id
            
            
            new_booking.visiting_group_name = vgroup.name
            
            new_booking.visiting_group = vgroup
            
            # TODO: add dates, but only after form validation
            #new_booking.requested_date = old_booking.requested_date
            #new_booking.valid_from = old_booking.valid_from
            #new_booking.valid_to = old_booking.valid_to
                
            new_booking.booking_day_id = booking_day_id
            new_booking.slot_row_position_id = slot_row_position_id
                
            DBSession.add(new_booking)
            DBSession.flush()
            remember_new_booking_request(new_booking)
            slot_row_position_state = 0
            if block_after_book:
                self.block_slot_helper(booking_day_id, slot_row_position_id, level=1)
                slot_row_position_state = 1
                
        return dict(text="hello",  booking_day_id=booking_day_id,  slot_row_position_id=slot_row_position_id, booking=new_booking,  visiting_group_name=vgroup.name,  success=True,  slot_row_position_state=slot_row_position_state)
        
    @expose("json")
    @validate(validators={'delete_req_booking_id':validators.Int(not_empty=True), 'activity_id':validators.Int(not_empty=True), 'visiting_group_id_id':validators.Int(not_empty=True)})
    @require(Any(is_user('root'), has_permission('staff'), msg='Only staff members may change booked booking properties'))
    def delete_booking_async(self,  delete_req_booking_id=0,  activity_id=0,  visiting_group_id=None):
        vgroup = DBSession.query(booking.VisitingGroup).filter('visiting_group.id='+visiting_group_id).one()
        booking_o = DBSession.query(booking.Booking).filter('id='+str(delete_req_booking_id)).one()
        remember_delete_booking_request(booking_o, changed_by=getLoggedInUser(request).user_id)
        deleteBooking(booking_o)

        return dict(text="hello",  delete_req_booking_id=delete_req_booking_id, visiting_group_name=vgroup.name,  success=True)
        
        
    @expose("json")
    @validate(validators={'delete_req_booking_id':validators.Int(not_empty=True), 'activity_id':validators.Int(not_empty=True), 'visiting_group_id_id':validators.Int(not_empty=True)})
    @require(Any(is_user('root'), has_permission('staff'), msg='Only staff members may change booked booking properties'))
    def unschedule_booking_async(self,  delete_req_booking_id=0,  activity_id=0,  visiting_group_id=None):
        vgroup = DBSession.query(booking.VisitingGroup).filter('visiting_group.id='+visiting_group_id).one()
        booking_o = DBSession.query(booking.Booking).filter('id='+str(delete_req_booking_id)).one()
        booking_o.last_changed_by_id = getLoggedInUser(request).user_id
        
        remember_unschedule_booking(booking=booking_o, slot_row_position=booking_o.slot_row_position, booking_day=booking_o.booking_day,  changed_by='')
        booking_o.booking_state = 0
        booking_o.booking_day_id = None
        booking_o.slot_row_position_id = None
        
        return dict(text="hello",  delete_req_booking_id=delete_req_booking_id, visiting_group_name=vgroup.name,  success=True)
        
