# -*- coding: utf-8 -*-
"""
Copyright 2010, 2011, 2012, 2013 Martin Eliasson

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

import pylons
from tg import expose, flash, require, url, request, redirect,  validate
from repoze.what.predicates import Any, is_user, has_permission
from hollyrosa.lib.base import BaseController
from hollyrosa.model import holly_couch
from hollyrosa.widgets.edit_visiting_group_program_request_form import create_edit_visiting_group_program_request_form
from tg import tmpl_context

import datetime,logging, json, time

log = logging.getLogger()

#...this can later be moved to the VisitingGroup module whenever it is broken out
from hollyrosa.controllers.common import has_level, DataContainer, getLoggedInUserId, reFormatDate

from hollyrosa.model.booking_couch import genUID, getBookingDayOfDate, getSchemaSlotActivityMap, getVisitingGroupByBoknr
from hollyrosa.controllers.booking_history import remember_tag_change
from hollyrosa.controllers.common import workflow_map,  DataContainer,  getLoggedInUserId,  change_op_map,  getRenderContent, getRenderContentDict,  computeCacheContent,  has_level,  reFormatDate, bokn_status_map
from hollyrosa.controllers.booking_history import remember_new_booking_request

from formencode import validators

__all__ = ['visiting_group_program_request']

age_group_data_raw = """{
	"identifier": "property",
	"items": [
		{
			"property": "barn",
			"unit": "smabarn",
			"age": "0-7",
			"age_group": "Smabarn",
			"value": 0,
			"from_date": "",
			"to_date": ""
		},
		{
			"property": "spar",
			"unit": "spar",
			"age": "8-9",
			"age_group": "Sparare",
			"value": 0,
			"from_date": "",
			"to_date": ""
		},
		{
			"property": "uppt",
			"unit": "uppt",
			"age": "10-11",
			"age_group": "Upptackare",
			"value": 0,
			"from_date": "",
			"to_date": ""
		},
		{
			"property": "aven",
			"unit": "aven",
			"age": "12-15",
			"age_group": "Aventyrare",
			"value": 0,
			"from_date": "",
			"to_date": ""
		},
		{
			"property": "utm",
			"unit": "utm",
			"age": "16-18",
			"age_group": "Utmanare",
			"value": 0,
			"from_date": "",
			"to_date": ""
		},
		{
			"property": "rover",
			"unit": "rover",
			"age": "18-25",
			"age_group": "Rover",
			"value": 0,
			"from_date": "",
			"to_date": ""
		},
		{
			"property": "led",
			"unit": "ledare",
			"age": "---",
			"age_group": "Ledare",
			"value": 0,
			"from_date": "",
			"to_date": ""
		}
	]
}"""


#property_list = []
#for tmp in age_group_data_raw['items']:
#    property_list.append(tmp['property'])


class VisitingGroupProgramRequest(BaseController):
    @expose()
    def login_vgroup(self, boknr=''):
        
        #lookup vgroup of boknr
        vgroup_list = getVisitingGroupByBoknr(holly_couch, boknr)
        if len(vgroup_list) == 0:
            flash(u"Det finns ingen grupp i systemet än med det bokningsnummer du angav.",'warning')
            raise redirect('/')
        else:
            raise redirect('edit_request', visiting_group_id=vgroup_list[0]['id'])
        return dict()
        
    
    	
    @expose('hollyrosa.templates.visiting_group_program_request_edit')
    @require(Any(is_user('user.erspl'), has_level('staff'), has_level('view'), msg='Only logged in users may view me properties'))
    def edit(self):
        tmpl_context.form = create_edit_visiting_group_program_request_form
        vgpr = dict()
        vgpr['name'] = 'test vgroup'
        vgpr['info'] = 'this is some info text'
        vgpr['contact_person'] = 'john doe'
        vgpr['from_date'] = '2012-06-01' 
        vgpr['to_date'] = '2012-06-06'
        
        #...construct the age group list. It's going to be a json document. Hard coded.
        #... if we are to partially load from database and check that we can process it, we do need to go from python to json. (and back)
        
        
        #vgpr['age_group_data'] = age_group_data
        
        #...construct a program request template. It's going to be a json document. Hard coded.
        
        return dict(visiting_group_program_request=vgpr)
        
        
        
    @expose('hollyrosa.templates.visiting_group_program_request_edit2')
    @require(Any(is_user('user.erspl'), has_level('staff'), has_level('view'), has_level('vgroup'), msg=u'Du måste vara inloggad för att få ändra i dina programönskemål'))    
    def edit_request(self, visiting_group_id=''):     	
        visiting_group_o = holly_couch[str(visiting_group_id)] 
        visiting_group_o.program_request_info = visiting_group_o.get('program_request_info','message to program!')
        visiting_group_o.program_request_have_skippers = visiting_group_o.get('program_request_have_skippers',0)
        visiting_group_o.program_request_miniscout = visiting_group_o.get('program_request_miniscout',0)
        
        #...construct a program request template. It's going to be a json document. Hard coded.
        #...supply booking request if it exists
        
        
        age_group_data_tmp = json.loads(age_group_data_raw)
        for tmp_item in age_group_data_tmp['items']:
        	log.debug('TMP ITEM' + str( tmp_item ))
        	tmp_item['from_date'] = visiting_group_o['from_date']
        	tmp_item['to_date'] = visiting_group_o['to_date']
        
        age_group_data = json.dumps(age_group_data_tmp)
        visiting_group_o.program_request_age_group = visiting_group_o.get('program_request_age_group', age_group_data)
        
        program_request_data_dict = {'identifier': 'id', 'items': [{'id':str(i), 'requested_date': visiting_group_o['from_date'], 'requested_time':'', 'requested_activity': '', 'age_sma':False, 'age_spar':False, 'age_uppt':False, 'age_aven':False, 'age_utm':False, 'age_rov':False, 'age_led':False, 'note':''} for i in range(35)] }
    
        #program_request_data_dict = {'identifier': 'rid', 'items': []}
        
        program_request_data = json.dumps(program_request_data_dict)
        visiting_group_o.program_request = visiting_group_o.get('program_request', program_request_data)
        
        return dict(visiting_group_program_request=visiting_group_o, reFormatDate=reFormatDate, bokn_status_map=bokn_status_map)
        
    @expose('hollyrosa.templates.visiting_group_program_request_edit')
    @require(Any(is_user('user.erspl'), has_level('staff'), has_level('view'), msg='Only logged in users may view me properties'))
    def view2(self):
        return dict(visiting_group_program_request=visiting_group_program_request)
        
        
    @expose()
    @require(Any(has_level('pl'), has_level('vgroup'), msg=u'Du måste vara inloggad för att få spara programönskemål'))
    def update_visiting_group_program_request(self, program_request_info='', contact_person='', contact_person_email='', contact_person_phone='', vgroup_id='', program_request_input='', have_skippers=False, miniscout=False, ready_to_process=False, age_group_input='', saveButton='', submitButton=''):
        visiting_group_id = str(vgroup_id)
        visiting_group_o = holly_couch[visiting_group_id]
        
        
        may_change_request_data = (0  == visiting_group_o['boknstatus'])
        visiting_group_o['contact_person'] = contact_person
        visiting_group_o['contact_person_email'] = contact_person_email
        visiting_group_o['contact_person_phone'] = contact_person_phone
        

        if may_change_request_data:    
            visiting_group_o['program_request_info'] = program_request_info
            visiting_group_o['program_request_miniscout'] = miniscout
            visiting_group_o['program_request_have_skippers'] = have_skippers
            visiting_group_o['program_request_age_group'] = age_group_input
            visiting_group_o['program_request'] = program_request_input
            
            
            #...SOME PROCESSING SHOULD ONLY BE DONE IF READY TO SHIP
            if 'True' == ready_to_process:
                visiting_group_o['boknstatus'] = 5 # TODO: use constant
        
            #...iterate through age_group_data, items is a list of dicts...
            age_group_data = json.loads(age_group_input)
            age_group_data_items = age_group_data['items']
        
            #...We should process the properties of the submitted form, not the other way around
        
            for tmp_age_group in age_group_data_items:
                process_property = tmp_age_group['property']
                log.debug('processing property:' + process_property )

                tmp_vgroup_property = None
                property_found = False
                for tmp_vgroup_property in visiting_group_o['visiting_group_properties'].values():
                    if tmp_vgroup_property['property'] == process_property:
                        property_found = True                    
                        break
            
                if property_found:
                    log.debug('old: ' + str(process_property) + '=' + str(tmp_vgroup_property['value']))
            
                    tmp_vgroup_property['value'] = tmp_age_group['value']
                    tmp_vgroup_property['from_date'] = tmp_age_group['from_date']
                    tmp_vgroup_property['to_date'] = tmp_age_group['to_date']
                    
                    log.debug('new: ' + process_property + '=' + str(tmp_age_group['value']))
                    #...ALSO MOVE DATES!
                else:
                    log.debug('property not found, what do we do?')
                
                    if 0 == tmp_age_group['value']:
                        log.debug('never mind, value is zero')
                    else:
                        #...we need to add an entry in the dict, first we need to know the lowest key number
                        lowest_key_number = 0
                        for tmp_key in visiting_group_o['visiting_group_properties'].keys():
                            if tmp_key > lowest_key_number:
                                lowest_key_number = int(tmp_key)
                        lowest_key_number +=1
                        log.debug('lowest_key_number: ' + str(lowest_key_number))
                        new_property_row = {u'description': tmp_age_group['age_group'], u'value': tmp_age_group['value'], u'from_date': tmp_age_group['from_date'], u'to_date': tmp_age_group['to_date'], u'property': tmp_age_group['property'], u'unit': tmp_age_group['unit']}
                        x = visiting_group_o['visiting_group_properties']
                        x[str(lowest_key_number)] = new_property_row
                        visiting_group_o['visiting_group_properties'] = x
                        log.debug(str(x))                        
            
            holly_couch[str(vgroup_id)] = visiting_group_o
            
        # We need to sanitize the dates that dojo/dijit supplies, they are not on the string form we preferre.
        # first, be ready to SANITIZE things like DATE RANGES 
        # 
        # for the program request , iterate through it
        if may_change_request_data:
            if 'True' == ready_to_process or True:
                program_request_list = json.loads(program_request_input)
                for tmp_request in program_request_list['items']:
                    log.debug('found request...' + str(tmp_request))
                    request_for_age_groups = [x[4:] for x in ['age_sma','age_spar','age_uppt','age_aven','age_utm','age_rov','age_led'] if tmp_request[x]]
                    if len(request_for_age_groups) > 0:                    
                        requested_date = tmp_request['requested_date'][:10]
                        requested_date_o = time.strptime(requested_date, "%Y-%M-%d" )
                        log.debug('requested_date: ' + requested_date)
                        requested_time = tmp_request['requested_time']
                        log.debug('requested_time: ' + requested_time)
                        requested_activity_id = tmp_request['requested_activity']
                        log.debug('activity_id: ' + requested_activity_id)
                        
                        #...now that we have all the data:
                        #...look up the day id of the date
                        booking_day_o = getBookingDayOfDate(holly_couch, tmp_request['requested_date'][:10]) # NEED TO SANITIZE...
                        log.debug(booking_day_o)
                        day_schema_id = booking_day_o['day_schema_id']
                        log.debug('day_schema id: ' + day_schema_id)
                        schema_o = holly_couch[day_schema_id]                        
                        
                        
                        #...given fm/em/evening, look up the matching slot_id. Probably the schema will be needed (and maybe index 0,1,2,3...)
                        tmp_activity_row = schema_o['schema'][requested_activity_id]
                        
                        log.debug('tmp_activity_row: ' + str(tmp_activity_row))
                        #...look through the list, lets say we have a time and we need the slot id matching that time
                        #   then the reasonable way is too look through all list entries being dicts and return slot id when time match found
                        activity_selection_map = dict()
                        activity_selection_map['activity.30'] = u'Storbåt'
                        
                        time_selection_lookup = dict(FM='10:00:00', EM='15:00:00', EVENING='20:00:00')
                        
                        #...EVENING should be called Kväll
                        #   It should be possible to book just 'any' water program
                        #   these maps with id-text transaltion should maybe be available in the templating engine
                        #   dont forget to give the date formatter to the templating engine
                        
                        time_selection_translator = dict(EVENING=u'kväll')
                                          
                        for tmp_slot_info in tmp_activity_row[1:]:
                            if (tmp_slot_info['time_from'] < time_selection_lookup[requested_time]) and (tmp_slot_info['time_to'] > time_selection_lookup[requested_time]):
                                match_slot_id = tmp_slot_info['slot_id']
                                log.debug('match for slot_id: ' + match_slot_id)
                                
                                # lets create a booking!   
                                
                                
                                
                                new_booking = dict(type='booking',  valid_from='',  valid_to='',  requested_date=requested_date, slot_id=match_slot_id, booking_day_id=booking_day_o['_id'],  subtype='program')
                                new_booking['visiting_group_id'] = str(vgroup_id)
                                new_booking['valid_from'] = visiting_group_o['from_date']
                                new_booking['valid_to'] = visiting_group_o['to_date']
                                new_booking['visiting_group_name'] = visiting_group_o['name']
                                new_booking['last_changed_by_id'] = getLoggedInUserId(request)
                                
                                activity_o = holly_couch[requested_activity_id]
                                content = u'%s (önskar %s %s %s) %s' % ( ' '.join(['$$%s'%a for a in request_for_age_groups ]) ,activity_selection_map.get(requested_activity_id, activity_o['title']), time.strftime("%d/%M", requested_date_o).replace('0',''), time_selection_translator.get(requested_time, requested_time), tmp_request['note'] )                                 
                                
                                new_booking['content'] = content
                                new_booking['cache_content'] = computeCacheContent(holly_couch[visiting_group_id], content)
                                new_booking['activity_id'] = requested_activity_id
            
                                
                                new_booking['booking_state'] = activity_o['default_booking_state']                                
                                                             
                                slot_map  = getSchemaSlotActivityMap(holly_couch, day_schema_id)
                                slot = slot_map[match_slot_id]
                                new_uid = genUID(type='booking')
                                
                                #...here we create the booking
                                holly_couch[new_uid] = new_booking
                                
                                #...remember the created booking
                                
                                remember_new_booking_request(holly_couch, booking=new_booking, changed_by=getLoggedInUserId())
                                break
                        
        raise redirect(request.referrer)
