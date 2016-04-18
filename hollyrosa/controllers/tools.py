# -*- coding: utf-8 -*-
"""
Copyright 2010-2016 Martin Eliasson

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

##import pylons
from tg import expose, flash, require, url, request, redirect,  validate
from repoze.what.predicates import Any, is_user, has_permission
from hollyrosa.lib.base import BaseController
from hollyrosa.model import genUID, holly_couch

import datetime,  StringIO,  time

#...this can later be moved to the VisitingGroup module whenever it is broken out
from tg import tmpl_context
import hashlib

from hollyrosa.widgets.edit_visiting_group_form import create_edit_visiting_group_form
from hollyrosa.widgets.edit_booking_day_form import create_edit_booking_day_form
from hollyrosa.widgets.edit_new_booking_request import  create_edit_new_booking_request_form
from hollyrosa.widgets.edit_book_slot_form import  create_edit_book_slot_form
from hollyrosa.widgets.validate_get_method_inputs import  create_validate_schedule_booking,  create_validate_unschedule_booking

from booking_history import  remember_workflow_state_change
from hollyrosa.controllers.common import workflow_map,  getLoggedInUser,  getRenderContent,  has_level

from hollyrosa.model.booking_couch import getAllActivityGroups,  getAllScheduledBookings,  getAllBookingDays,  getAllVisitingGroups,  getAllActivities
from hollyrosa.model.booking_couch import getAgeGroupStatistics, getTagStatistics, getSchemaSlotActivityMap, getActivityTitleMap, getBookingDays, getAllUtelunchBookings, getActivityStatistics
__all__ = ['tools']

workflow_submenu = """<ul class="any_menu">
        <li><a href="overview">overview</a></li>
        <li><a href="view_nonapproved">non-approved</a></li>
        <li><a href="view_unscheduled">unscheduled</a></li>
        <li><a href="view_scheduled">scheduled</a></li>
        <li><a href="view_disapproved">dissapproved</a></li>
    </ul>"""

class Tools(BaseController):
    def view(self, url):
        """Abort the request with a 404 HTTP status code."""
        abort(404)
    
    
    @expose('hollyrosa.templates.tools_show')
    def show(self,  day=None):
        """Show an overview of all bookings"""
        if day == None:
            day = datetime.datetime.today().date().strftime("%Y-%m-%d")
            
        activity_groups = [h.value for h in getAllActivityGroups(holly_couch)]
        return dict(show_day=day,  activity_groups=activity_groups)



    def get_severity(self, visiting_group,  severity):
        if visiting_group.get('hide_warn_on_suspect_bookings', False) == True:
            severity = 0
        return severity


    def fn_sort_problems_by_severity(self, a, b):
        return cmp(b['severity'], a['severity'])
        

    @expose('hollyrosa.templates.view_sanity_check_property_usage')
    @require(Any(has_level('staff'), has_level('pl'),  msg='Only PL or staff members can change booking state, and only PL can approve/disapprove'))
    def sanity_check_property_usage(self):
        
        #...iterate through all bookings, we are only interested in scheduled bookings
        bookings = getAllScheduledBookings(holly_couch, limit=1000000) 
        booking_days_map = dict()
        for bd in getAllBookingDays(holly_couch):
            booking_days_map[bd.doc['_id']] = bd.doc
            
        visiting_group_map = dict()
        for vg in getAllVisitingGroups(holly_couch):
            visiting_group_map[vg.key[1]] = vg.doc
            
        #activity_map = dict()
        activity_title_map = getActivityTitleMap(holly_couch)
        
        problems = list()
        for tmp_bx in bookings:
            tmp_b = tmp_bx.doc
            tmp_b_day_id = tmp_b['booking_day_id']
            tmp_b_day = booking_days_map[tmp_b_day_id]
            
        #    if not activity_map.has_key(tmp_b_day['day_schema_id']):
        #        activity_map[tmp_b_day['day_schema_id']] = getSchemaSlotActivityMap(holly_couch, tmp_b_day['day_schema_id'])

        #    tmp_activity_map = activity_map[tmp_b_day['day_schema_id']]
                 
            if None != tmp_b_day: # and tmp_b_day.date >= datetime.date.today():
                if tmp_b['visiting_group_id'] != '' and (False == tmp_b.get('hide_warn_on_suspect_booking',  False)):
                    tmp_date = tmp_b_day['date']
                    tmp_content = activity_title_map[tmp_b['activity_id']] + ' ' + tmp_b['content']
                    tmp_b_visiting_group = visiting_group_map[tmp_b['visiting_group_id']]

                    
                    if not tmp_b_visiting_group.has_key('from_date'):
                        problems.append(dict(booking=tmp_b, msg='visiting group %s has no from_date' % tmp_b_visiting_group['visiting_group_name'], severity=100))
                    else:
                        if tmp_b_visiting_group['from_date'] > tmp_date:
                            problems.append(dict(booking=tmp_b, msg='arrives at %s but booking %s is at %s' %(str(tmp_b_visiting_group['from_date']), tmp_content ,str(tmp_date)), severity=10))
    
                        if tmp_b_visiting_group['from_date'] == tmp_date:
                            problems.append(dict(booking=tmp_b, msg='arrives same day as booking %s, at %s' % (tmp_content, str(tmp_b_visiting_group['from_date'])), severity=self.get_severity(tmp_b_visiting_group, 1)))
                        
                    if tmp_b_visiting_group['to_date'] < tmp_date:
                        problems.append(dict(booking=tmp_b, msg='leves at %s but booking %s is at %s' % (str(tmp_b_visiting_group['to_date']), tmp_content , str(tmp_date)), severity=10))
    
                    if tmp_b_visiting_group['to_date'] == tmp_date:
                        problems.append(dict(booking=tmp_b, msg='leves same day as booking %s, at %s' % (tmp_content, str(tmp_b_visiting_group['to_date'])), severity=self.get_severity(tmp_b_visiting_group, 1)))
                    
                    tmp_content = tmp_b['content']
                    for tmp_prop in tmp_b_visiting_group['visiting_group_properties'].values():
                        checks = [x+tmp_prop['property'] for x in ['$$','$',  '$#','#']]
                        
                        for check in checks:
                            if check in tmp_content:
                                if tmp_prop['from_date'] > tmp_date:
                                    problems.append(dict(booking=tmp_b, msg='property $' + tmp_prop['property'] + ' usable from ' + str(tmp_prop['from_date']) + ' but booking is at ' + str(tmp_date), severity=10))
    
                                if tmp_prop['from_date'] == tmp_date:
                                    problems.append(dict(booking=tmp_b, msg='property $' + tmp_prop['property'] + ' arrives at ' + str(tmp_prop['from_date']) + ' and booking is the same day', severity=self.get_severity(tmp_b_visiting_group, 1)))
                                    
                                if tmp_prop['to_date'] < tmp_date:
                                    problems.append(dict(booking=tmp_b, msg='property $' + tmp_prop['property'] + ' usable to ' + str(tmp_prop['to_date']) + ' but booking is at ' + str(tmp_date), severity=10))
    
                                if tmp_prop['to_date'] == tmp_date:
                                    problems.append(dict(booking=tmp_b, msg='property $' + tmp_prop['property'] + ' leavs at ' + str(tmp_prop['to_date']) + ' and booking is the same day ', severity=self.get_severity(tmp_b_visiting_group, 1)))
    
                                break # there can be more than one match in checks
        problems.sort(self.fn_sort_problems_by_severity)
        return dict (problems=problems,  visiting_group_map=visiting_group_map)
        
        
    @expose('hollyrosa.templates.activity_statistics')
    @require(Any(has_level('staff'), has_level('pl'), msg='Only PL or staff members can take a look at people statistics'))
    def activity_statistics(self):
        activity_statistics = getActivityStatistics(holly_couch)
        
        #...return activity, activity_group, bookings
        result = list()
        for tmp_activity_stat in activity_statistics:
            tmp_key = tmp_activity_stat.key
            tmp_value = tmp_activity_stat.value
            
            tmp_activity_id = tmp_key[0]
            tmp_activity = holly_couch[tmp_activity_id]
            tmp_activity_name = tmp_activity['title']
            activity_group_name = holly_couch[tmp_activity['activity_group_id']]['title']
            totals = tmp_value
            row = dict(activity=tmp_activity_name, activity_group=activity_group_name, totals=totals)
            result.append(row)
        
        return dict(statistics=result)
    
        
    @expose('hollyrosa.templates.visitor_statistics')
    @require(Any(has_level('staff'), has_level('pl'), msg='Only PL or staff members can take a look at people statistics'))
    def visitor_statistics(self):
        
        # TODO: this complete calculation has to be redone 
        #       since visiting group properties doesent 
        #       exist as a 'table' any more.
        #
        # One way could be to make a list of all days.
        #   This list is filled with dicts containing the result
        #   The dicts are filled in by iterating through the visiting groups
        #   properties
        #
        # If one were to make a really complicated couch map, you would 
        # create a key [date, property-from-vgroup-properties] -> value and then sum it using reduce :)
        #
        #
        #
        #
        #        
        
        statistics_totals = getAgeGroupStatistics(holly_couch, group_level=1)
        statistics = getAgeGroupStatistics(holly_couch)
        
        property_names = dict()
        totals = dict() # totals = list()
        for tmp in statistics:   
            tmp_key = tmp.key
            tmp_value = tmp.value            
            
            tmp_property = tmp_key[1]
            tmp_date_x = tmp_key[0]
            tmp_date = datetime.date(tmp_date_x[0], tmp_date_x[1], tmp_date_x[2]) #'-'.join([str(t) for t in tmp_date])

            tot = totals.get(tmp_date, dict())
            tot[tmp_property] = int(tmp_value)
            property_names[tmp_property] = 1 # kepiong track of property names used
            totals[tmp_date] = tot

        #...same thing but now for aggrgate statistics
        all_totals = list()
        for tmp in statistics_totals:
            tmp_key = tmp.key
            tmp_value = tmp.value
            
            tmp_date_x = tmp_key[0]
            tmp_date = datetime.date(tmp_date_x[0], tmp_date_x[1], tmp_date_x[2]) #'-'.join([str(t) for t in tmp_date])

            tot = totals.get(tmp_date, dict())
            #...for now we need to protect against tot=0 giving zero division errors
            if tmp_value == 0:
                tmp_value = 1
            tot['tot'] = tmp_value
            totals[tmp_date] = int(tmp_value)

            mark = '#444;'
            if tot['tot'] < 250:
                mark = '#484;'
            elif tot['tot'] < 500:
                mark = '#448;'
            elif tot['tot'] < 1000:
                mark = '#828;'
            else:
                mark = '#844;'
            all_totals.append((tmp_date, tot, mark))


        property_ns = ['spar','uppt','aven','utm']
        l = list()
        for n in property_names.keys():
            if n not in property_ns:
                l.append(n)

        
        return dict(property_names=l, people_by_day=all_totals)






    @expose('hollyrosa.templates.vodb_statistics')
    @require(Any(has_level('staff'), has_level('pl'), msg='Only PL or staff members can take a look at people statistics'))
    def vodb_statistics(self):
        """
        This method is intended to show the number of participants in different workflow state (preliminary, etc)
        """
        statistics_totals = getTagStatistics(holly_couch, group_level=1)
        statistics = getTagStatistics(holly_couch, group_level=2)
        
        #...find all tags that is used and perhaps filter out unwanted ones.
        
        tags = dict()
        totals = dict() 
        for tmp in statistics:
            tmp_key = tmp.key
            tmp_value = tmp.value                        
            tmp_tag = tmp_key[1]
            
            if tmp_tag[:4] == 'vodb':
                tmp_date_x = tmp_key[0]
                tmp_date = datetime.date(tmp_date_x[0], tmp_date_x[1], tmp_date_x[2]) 
            
                tot = totals.get(tmp_date, dict())
                tot[tmp_tag] = int(tmp_value)
                sum = tot.get('tot',0) 
                sum += int(tmp_value)
                tot['tot'] = sum
                tags[tmp_tag] = 1
                totals[tmp_date] = tot
                
        all_totals=list()
        for tmp in statistics_totals:   
            tmp_key = tmp.key
            tmp_value = tmp.value                        
            tmp_date_x = tmp_key[0]
            tmp_date = datetime.date(tmp_date_x[0], tmp_date_x[1], tmp_date_x[2]) 
            
            tot = totals.get(tmp_date, dict(tot=0))
            mark = '#444;'                
            if tot['tot'] < 250:
                mark = '#484;'
            elif tot['tot'] < 500:
                mark = '#448;'
            elif tot['tot'] < 1000:
                mark = '#828;'
            else:
                mark = '#844;'
            all_totals.append((tmp_date, tot, mark))

        
        return dict(tags=['vodb:definitiv',u'vodb:preliminär',u'vodb:förfrågan', 'vodb:na'], people_by_day=all_totals)



    @expose('hollyrosa.templates.booking_day_summary')
    @require(Any(has_level('staff'), has_level('pl'), msg='Only PL or staff members can take a look at booking statistics'))
    def booking_statistics(self):
        """Show a complete booking day"""
        abort(501)
        slot_rows = DBSession.query(booking.SlotRow).options(eagerload('activity'))
        slot_rows_n = []
        for s in slot_rows:
            slot_rows_n.append(s)

        #...first, get booking_day for today
        bookings = DBSession.query(booking.Booking).all()
        
        #...additions - counting properties
        visiting_groups = DBSession.query(booking.VisitingGroup).all() #join(booking.VistingGroupProperty).all()
        vgroup_properties = DBSession.query(booking.VistingGroupProperty).all()
        
        activity_totals = dict()
        totals = 0
        for s in bookings:
            if s.booking_day_id != None:
                activity_count_list, activity_property_count = activity_totals.get(s.activity.id, (list(), {}))
                
                #...check in content for properties
                tmp_content = s.content
                tmp_visiting_group = s.visiting_group
               
                if None != tmp_visiting_group:
                    tmp_vgroup_properties = tmp_visiting_group.visiting_group_property
                    for tmp_vgroup_property in tmp_vgroup_properties:
                        if '$'+tmp_vgroup_property.property in tmp_content:
                            tmp_count_x = activity_property_count.get(tmp_vgroup_property.property, 0) + int(tmp_vgroup_property.value)
                            activity_property_count[tmp_vgroup_property.property] = tmp_count_x
                            tmp_count_all = activity_property_count.get('ALL', 0) + int(tmp_vgroup_property.value)
                            activity_property_count['ALL'] = tmp_count_all


                activity_count_list.append(s)
                activity_totals[s.activity.id] = (activity_count_list, activity_property_count)
                totals += 1


        return dict(slot_rows=slot_rows_n,  bookings=activity_totals, totals=totals)
        
        
    @expose('hollyrosa.templates.sannah_overview')
    @require(Any(has_level('staff'), has_level('pl'),  msg='Only PL can take a look at people statistics'))
    def sannah(self):
        #...get all booking days in the future
        today = datetime.date.today().strftime('%Y-%m-%d')
        all_booking_days = [b.doc for b in getBookingDays(holly_couch, from_date=today)]
        
        #...get all utelunch bookings
        utelunch_bookings = getAllUtelunchBookings(holly_couch)
        
        #...make dict mapping booking day id (key) to bookings
        utelunch_dict = dict()
        for ub in utelunch_bookings:
            
            tmp_booking_list = utelunch_dict.get(ub.key, list())
            tmp_booking_list.append(ub.doc)
            utelunch_dict[ub.key] = tmp_booking_list        
        
        log.info( utelunch_dict )
        return dict(booking_days=all_booking_days, utelunches=utelunch_dict)


    @expose()
    @require(Any(has_level('pl'),  msg='Only PL can take a look at booking statistics'))
    def set_booking_day_schema_ids(self):
        booking_days = [b.doc for b in getAllBookingDays(holly_couch)]
        for bdy in booking_days:
            if bdy['date'] <= '2012-07-22' or bdy['date'] > '2012<07-29':
                bdy['day_schema_id'] = 'day_schema.2012'
                holly_couch[bdy['_id']] = bdy
            
        raise redirect('/')
        
        
    @expose()
    @require(Any(has_level('pl'),  msg='Only PL can poke around the schemas'))
    def create_living_schema(self):
        ew_id = genUID(type='living_schema')
        schema = dict(type='day_schema',  subtype='room',  title='room schema 2013',  activity_group_ids=["activity_groups_ids", "roomgroup.fyrbyn", "roomgroup.vaderstracken", "roomgroup.vindarnashus","roomgroup.tunet",
        "roomgroup.skrakvik","roomgroup.tc","roomgroup.alphyddorna","roomgroup.gokboet","roomgroup.kojan"])
        all_activities = getAllActivities(holly_couch)
        
        #...create some living, map to all activities in ag groups house
        i=0
        z=0
        tmp_schema = dict()
        for tmp_act in list(all_activities):
            print tmp_act
            if tmp_act.has_key('activity_group_id') or True:
                if tmp_act.doc['activity_group_id'][:9] == 'roomgroup':            
                    z += 1
                    tmp_id = dict(zorder=z,  id=tmp_act['id'])
                    tmp_fm = dict(time_from='00:00:00', time_to='12:00:00',  duration='12:00:00', title='FM',  slot_id='live_slot.' + str(i) )
                    i +=1
                    tmp_em = dict(time_from='12:00:00', time_to='23:59:00',  duration='12:00:00', title='EM',  slot_id='live_slot.' + str( i) )
                    #...create fm and em but nothing more
                    i+=1
            
                    tmp_schema[tmp_act['id']] = [tmp_id,  tmp_fm,  tmp_em]
        
        schema['schema'] = tmp_schema
        holly_couch[ew_id] = schema
        
        
        raise redirect(request.referer)
