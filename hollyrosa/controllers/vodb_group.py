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
from hollyrosa.widgets.edit_vodb_group_form import create_edit_vodb_group_form
from tg import tmpl_context

import datetime,logging, json, time, types

log = logging.getLogger()

#...this can later be moved to the VisitingGroup module whenever it is broken out
from hollyrosa.controllers.common import has_level, DataContainer, getLoggedInUserId, reFormatDate

from hollyrosa.model.booking_couch import genUID, getBookingDayOfDate, getSchemaSlotActivityMap, getVisitingGroupByBoknr, getAllVisitingGroups, getTargetNumberOfNotesMap, getAllTags, getNotesForTarget, getBookingsOfVisitingGroup, getBookingOverview, getBookingEatOverview, getDocumentsByTag, getVisitingGroupsByVodbState, getVisitingGroupsByBoknstatus, dateRange
from hollyrosa.controllers.booking_history import remember_tag_change
from hollyrosa.controllers.common import workflow_map,  DataContainer,  getLoggedInUserId,  change_op_map,  getRenderContent, getRenderContentDict,  computeCacheContent,  has_level,  reFormatDate, bokn_status_map, vodb_status_map, make_object_of_vgdictionary
from hollyrosa.controllers.booking_history import remember_new_booking_request

from formencode import validators

__all__ = ['VODBGroup']

vodb_live_times = [u'fm', u'em', u'evening']
vodb_eat_times = [u'breakfast', u'lunch', u'lunch_arrive', u'lunch_depart', u'dinner']
vodb_eat_times_options = [u'indoor', u'outdoor', u'own']
vodb_live_times_options = [u'indoor',u'outdoor',u'daytrip']
#vodb_live_cols = 




class VODBGroup(BaseController):
    
    #
    #...list all groups...Borrow from Visiting group.... need to refactor out commons
    #   thinking that all groups share some very basic common stuff. at least they should in the long run
    #
    #   think about what in the template should be different...
    

    @expose('hollyrosa.templates.vodb_group_view_all')
    @require(Any(is_user('erspl'), has_level('staff'), msg='Only staff members and viewers may view visiting group properties'))
    def view_all(self):
        visiting_groups = [v.doc for v in getAllVisitingGroups(holly_couch)] 
        remaining_visiting_groups_map = dict()
        has_notes_map = getTargetNumberOfNotesMap(holly_couch)
        return dict(visiting_groups=visiting_groups, remaining_visiting_group_names=remaining_visiting_groups_map.keys(), program_state_map=bokn_status_map, vodb_state_map=bokn_status_map, reFormatDate=reFormatDate, all_tags=[t.key for t in getAllTags(holly_couch)], has_notes_map=has_notes_map)


    @expose('hollyrosa.templates.vodb_group_view_all')
    @require(Any(is_user('erspl'), has_level('staff'),   msg='Only staff members and viewers may view visiting group properties'))
    def view_tags(self, tag):
        # TODO>: rename and maybe only return visiting groups docs ?
        visiting_groups = [v.doc for v in getDocumentsByTag(holly_couch, tag)] 
        remaining_visiting_groups_map = dict()
        has_notes_map = getTargetNumberOfNotesMap(holly_couch)
        return dict(visiting_groups=visiting_groups,  remaining_visiting_group_names=remaining_visiting_groups_map.keys(), bokn_status_map=bokn_status_map,  vodb_state_map=bokn_status_map,  program_state_map=bokn_status_map,  reFormatDate=reFormatDate, all_tags=[t.key for t in getAllTags(holly_couch)], has_notes_map=has_notes_map)


    @expose('hollyrosa.templates.vodb_group_view_all')
    @validate(validators={'program_state':validators.Int(not_empty=True)})
    @require(Any(is_user('root'), has_level('staff'), has_level('view'), msg='Only staff members and viewers may view visiting group properties'))
    def view_program_state(self,  program_state=None):
        #boknstatus=boknstatus[:4] # amateurish quick sanitation
        #visiting_groups = get_visiting_groups_with_boknstatus(boknstatus) 
        visiting_groups =[v.doc for v in getVisitingGroupsByBoknstatus(holly_couch, program_state)]
        v_group_map = dict()
        has_notes_map = getTargetNumberOfNotesMap(holly_couch)  
        return dict(visiting_groups=visiting_groups, remaining_visiting_group_names=v_group_map.keys(), program_state_map=bokn_status_map, vodb_state_map=bokn_status_map, reFormatDate=reFormatDate, all_tags=[t.key for t in getAllTags(holly_couch)], has_notes_map=has_notes_map)


    @expose('hollyrosa.templates.vodb_group_view_all')
    @validate(validators={'vodb_state':validators.Int(not_empty=True)})
    @require(Any(is_user('root'), has_level('staff'), has_level('view'), msg='Only staff members and viewers may view visiting group properties'))
    def view_vodb_state(self,  vodb_state=None):
        visiting_groups =[v.doc for v in getVisitingGroupsByVodbState(holly_couch, vodb_state)]
        v_group_map = dict()
        has_notes_map = getTargetNumberOfNotesMap(holly_couch)  
        return dict(visiting_groups=visiting_groups, remaining_visiting_group_names=v_group_map.keys(), program_state_map=bokn_status_map, vodb_state_map=bokn_status_map, reFormatDate=reFormatDate, all_tags=[t.key for t in getAllTags(holly_couch)], has_notes_map=has_notes_map)

  
    @expose('hollyrosa.templates.vodb_group_edit')
    @require(Any(is_user('user.erspl'), has_level('staff'), has_level('view'), msg='Only logged in users may view me properties'))
    def edit_group_data(self, visiting_group_id=''):
        visiting_group_x = holly_couch[visiting_group_id]
        tmpl_context.form = create_edit_vodb_group_form
        
        #...construct the age group list. It's going to be a json document. Hard coded.
        #... if we are to partially load from database and check that we can process it, we do need to go from python to json. (and back)
        #...construct a program request template. It's going to be a json document. Hard coded.
        
        
        
        if not visiting_group_x.has_key('vodb_status'):
            visiting_group_x['vodb_status'] = 0
        
        for k in ['vodb_contact_name', 'vodb_contact_email', 'vodb_contact_phone', 'vodb_contact_address']:
            if not visiting_group_x.has_key(k):
                visiting_group_x[k] = ''
                
        visiting_group_o = make_object_of_vgdictionary(visiting_group_x)
         
        return dict(vodb_group=visiting_group_o, reFormatDate=reFormatDate, bokn_status_map=workflow_map)


    def newOrExistingVgroupId(self, a_id):
        is_new = False
        r_id = a_id
                 
        if None == a_id or a_id == '':
            is_new = True
            r_id = genUID(type='visiting_group')
        #elif 'visiting_group' not in id:
        #    is_new = True
        #    r_id = 'visiting_group.'+id 
            
        return is_new, r_id
    

    @expose()
    @validate(create_edit_vodb_group_form, error_handler=edit_group_data)
    @require(Any(is_user('root'), has_level('staff'), msg='Only staff members may change visiting group properties'))
    def save_vodb_group_properties(self, id='', boknr='', name='', info='', camping_location='', vodb_contact_name='', vodb_contact_phone='', vodb_contact_email='', vodb_contact_address='', from_date='', to_date='', visiting_group_properties=None):
        #...how do we handle new groups? Like new visiting_group, right?
        #   better have type=visiting_group for all groups and then have subtypes=group, course, daytrip, funk, etc for filtering/deciding on additional capabillities
        #
        is_new, vgroup_id = self.newOrExistingVgroupId(id) 
                
                
        if is_new:
            program_state = 0
            vodb_state = 0
            visiting_group_o = dict(type='visiting_group')
      
        else:
            visiting_group_o = holly_couch[vgroup_id]

        #...fill in data
        visiting_group_o['name'] = name
        visiting_group_o['info'] = info
        visiting_group_o['from_date'] = str(from_date)
        visiting_group_o['to_date'] = str(to_date)
        visiting_group_o['vodb_contact_name'] = vodb_contact_name
        visiting_group_o['vodb_contact_email'] = vodb_contact_email
        visiting_group_o['vodb_contact_phone'] = vodb_contact_phone
        visiting_group_o['vodb_contact_address'] = vodb_contact_address
        
        visiting_group_o['boknr'] = boknr
        #visiting_group_o['password'] = password
        if is_new:
            visiting_group_o['boknstatus'] = program_state
            visiting_group_o['vodbstatus'] = vodb_state
        visiting_group_o['camping_location'] = camping_location
        
        visiting_group_property_o = dict()
            
            
        #...populate / change properties



        # TODO: refactor        
        #...remove non-used params !!!! Make a dict and see which are used, remove the rest
        unused_params = {}        
        used_param_ids = []
        if  visiting_group_o.has_key('visiting_group_properties'):
            used_param_ids = visiting_group_o['visiting_group_properties'].keys()
        
        for param in visiting_group_properties:
            is_new_param = False
            if param['property'] != '' and param['property'] != None:
                if param['id'] != '' and param['id'] != None:
                    visiting_group_property_o[param['id']] = dict(property=param['property'],  value=param.get('value',''),  description=param.get('description',''),  unit=param.get('unit',''),  from_date=str(param['from_date']),  to_date=str(param['to_date']))
                else:
                    #...compute new unsued id
                    # TODO: these ids are not perfectly unique. It could be a problem with dojo grid
                    
                    new_id_int = 1
                    while str(new_id_int) in used_param_ids:
                        new_id_int += 1
                    used_param_ids.append(str(new_id_int))
                    
                    visiting_group_property_o[str(new_id_int)] = dict(property=param['property'],  value=param.get('value',''),  description=param.get('description',''),  unit=param.get('unit',''),  from_date=str(param['from_date']),  to_date=str(param['to_date']))
                    
        # no need to delete old params, but we need to add to history how params are changed and what it affects
        
        #...now we have to update all cached content, so we need all bookings that belong to this visiting group
        
        visiting_group_o['visiting_group_properties'] = visiting_group_property_o
        
        # TODO: IMPORTANT TO FIX LATER
        # TODO: refactor
        bookings = getBookingsOfVisitingGroup(holly_couch, vgroup_id,  None)
        for tmp in bookings:
            tmp_booking = tmp.doc
            
            new_content = computeCacheContent(visiting_group_o, tmp_booking['content'])
            if new_content != tmp_booking['cache_content'] :
            
                tmp_booking['cache_content'] = new_content
                tmp_booking['last_changed_by'] = getLoggedInUserId(request)
                
                # TODO: change booking status (from whatever, since the text has changed)
                
                
                # TODO: remember booking history change
                
                
                holly_couch[tmp_booking['_id']] = tmp_booking
            
        
        holly_couch[vgroup_id] = visiting_group_o
        
        if visiting_group_o.has_key('_id'):
            raise redirect('/vodb_group/view_vodb_group?visiting_group_id='+visiting_group_o['_id'])
        raise redirect('/vodb_group/view_all')
        
        
        
    def dateGen(self, from_date, to_date):
        tmp_result = datetime.datetime.strptime(from_date, "%Y-%m-%d")
        
        yield from_date
        delta = datetime.timedelta(1) #).strftime('%Y-%m-%d')        
        tmp_result_str = from_date        
        while tmp_result_str != to_date:
            tmp_result = tmp_result + delta
            tmp_result_str = tmp_result.strftime('%Y-%m-%d')
            yield tmp_result_str
        
    
        
    def make_empty_vodb_sheet(self, from_date, to_date, times, cols):
        """
        makes an empty sheet with all date-times for among others the live sheet
        """
    
        r1_items = list()
        #rid = lowest_rid
        for tmp_date in self.dateGen(from_date, to_date):
            for tmp_time in times:
                it = dict(date=tmp_date, time=tmp_time)
                it['rid'] = self.get_composite_key(it)
                for tmp_col in cols:
                    it[tmp_col] = 0
                    
                r1_items.append(it)
                #rid += 1

        return dict(identifier='rid', items=r1_items)
        
        
    def make_empty_vodb_live_sheet(self, from_date, to_date):
        return self.make_empty_vodb_sheet(from_date, to_date, vodb_live_times, vodb_live_times_options)
        
    def make_empty_vodb_eat_sheet(self, from_date, to_date):
        return self.make_empty_vodb_sheet(from_date, to_date, vodb_eat_times, vodb_eat_times_options)
        

    
    
    def get_composite_key(self, row):
        # refactor out
        # store composite key and use it as rid and things will go much faster.
        d = dict()
        d[u'fm']=u'1'
        d[u'em']=u'2'
        d[u'evening']=u'3'
        d[u'breakfast'] = u'10'
        d[u'lunch'] = u'11'
        d[u'lunch_arrive'] = u'12'
        d[u'lunch_depart'] = u'13'
        d[u'dinner'] = u'18'
        
        return row['date'] + u'_' +d.get(row['time'],'unknown')
        
        
    def fn_cmp_composite_key(self, a, b):
        return cmp(self.get_composite_key(a), self.get_composite_key(b))
        
        
    # the expression del referrs to Data Eat Live. LED was too confusing so I choose DEL :)    

    def compute_all_used_vgroup_tags(self, tags, rows):
        all_current_vgroup_tags = dict()
        for tmp_key in tags:
            all_current_vgroup_tags[tmp_key] = 1
            
        for tmp_row in rows:
            for tmp_key in tmp_row.keys():
                if ((tmp_key != 'date') and (tmp_key != 'time')):
                    if not all_current_vgroup_tags.has_key(tmp_key):
                        all_current_vgroup_tags[tmp_key] = 1
        return all_current_vgroup_tags

        
    @expose('hollyrosa.templates.vodb_group_edit_sheet')
    @require(Any(is_user('user.erspl'), has_level('staff'), has_level('view'), msg='Only logged in users may view me properties'))
    def edit_group_sheet(self, visiting_group_id=''):
        visiting_group_o = holly_couch[visiting_group_id]
        tmpl_context.form = create_edit_vodb_group_form
        
        #...construct the age group list. It's going to be a json document. Hard coded.
        #... if we are to partially load from database and check that we can process it, we do need to go from python to json. (and back)
        #...construct a program request template. It's going to be a json document. Hard coded.
        
        
        if not visiting_group_o.has_key('vodb_status'):
            visiting_group_o['vodb_status'] = 0
        for k in ['vodb_contact_name', 'vodb_contact_email', 'vodb_contact_phone', 'vodb_contact_address']:
            if not visiting_group_o.has_key(k):
                visiting_group_o[k] = ''
        
        #...step 1 - create some random data just to show you know what it looks like
        # the real tricky part is to construct that merge part that does two things:
        # 1. we cant have rows with dates outside the range
        # 2. if we miss rows with certain dates, we should insert them
        live_data = visiting_group_o.get('vodb_live_sheet', dict(identifier='rid', items=[]))
        empty_vodb_live_sheet = self.make_empty_vodb_live_sheet(visiting_group_o['from_date'], visiting_group_o['to_date'])
        row_lookup = dict()
        for tmp_row in empty_vodb_live_sheet['items']:
            row_lookup[tmp_row['rid']] = tmp_row
        
        for tmp_row in live_data['items']:
            composite_key = tmp_row['rid'] 
            if row_lookup.has_key(composite_key):
                del row_lookup[composite_key]
            
        for row_left in row_lookup.values():
            live_data['items'].append(row_left)
            
        #...re-sort the rows!
        live_data_items = live_data['items']
        live_data_items.sort(self.fn_cmp_composite_key)
        live_data['items'] = live_data_items

        # todo        
        # tags in yellow box
        # What do we do with tag data when a tag is deleted?
        # What do we do with tag data when a tag is added
        # Data for non existing tag, shouldnt it be shown anyway? 
        # Can we purge data that has no tag associated?
        #
        # When later saving all this, we should compute a cache content that can be used in future queries / views so we 
        # can start compute collected information
        #
        #
        # first of all, a general mega overview...
        #
        # we also soon will need som kind of subtyping
        
        
             
        eat_data = visiting_group_o.get('vodb_eat_sheet', dict(identifier='rid', items=[]))     
        empty_vodb_eat_sheet = self.make_empty_vodb_eat_sheet(visiting_group_o['from_date'], visiting_group_o['to_date'])
        row_lookup = dict()
        for tmp_row in empty_vodb_eat_sheet['items']:
            row_lookup[tmp_row['rid']] = tmp_row
        
        for tmp_row in eat_data['items']:
            composite_key = tmp_row['rid'] 
            if row_lookup.has_key(composite_key):
                del row_lookup[composite_key]
            
        for row_left in row_lookup.values():
            eat_data['items'].append(row_left)
            
        #...re-sort the rows!
        eat_data_items = eat_data['items']
        eat_data_items.sort(self.fn_cmp_composite_key)
        eat_data['items'] = eat_data_items
            
        
       
        tag_data = visiting_group_o.get('vodb_tag_sheet', dict(identifier='rid', items=[]))     
        
        all_current_vgroup_tags = self.compute_all_used_vgroup_tags(visiting_group_o['tags'], tag_data['items'])
        #all_current_vgroup_tags = dict()
        #for tmp_key in visiting_group_o['tags']:
        #    all_current_vgroup_tags[tmp_key] = 1
        #    
        #
        #for tmp_row in occu_data['items']:
        #    for tmp_key in tmp_row.keys():
        #        if ((tmp_key != 'date') and (tmp_key != 'time')):
        #            if not all_current_vgroup_tags.has_key(tmp_key):
        #                all_current_vgroup_tags[tmp_key] = 1
        
        empty_vodb_tag_sheet = self.make_empty_vodb_sheet(visiting_group_o['from_date'], visiting_group_o['to_date'],vodb_live_times, all_current_vgroup_tags.keys()) 
        
        row_lookup = dict()
        for tmp_row in empty_vodb_tag_sheet['items']:
            row_lookup[tmp_row['rid']] = tmp_row
        
        for tmp_row in tag_data['items']:
            composite_key = tmp_row['rid'] 
            if row_lookup.has_key(composite_key):
                del row_lookup[composite_key]
            
        for row_left in row_lookup.values():
            tag_data['items'].append(row_left)
            
        #...re-sort the rows!
        tag_data_items = tag_data['items']
        tag_data_items.sort(self.fn_cmp_composite_key)
        tag_data['items'] = tag_data_items
        
        
        
        visiting_group_o['vodb_live_sheet'] = json.dumps( live_data )
        visiting_group_o.vodb_eat_sheet = json.dumps( eat_data )
        visiting_group_o.vodb_tag_sheet = json.dumps( tag_data )
        
        
        #...we also must fix the tag_grid layout since its dynamic
        
        tag_layout_tags = json.dumps(visiting_group_o['tags'])
        
        return dict(vodb_group=visiting_group_o, tag_layout_tags=tag_layout_tags, reFormatDate=reFormatDate, bokn_status_map=workflow_map)
    
    
                    
    def vodb_sheet_property_substitution(self, rows, headers, properties):
        """
        TODO: WEE NEED TO TRIGGER THIS IF ANY PROPERTIES EVER CHANGE
        """
        for row in rows:
            for k in headers:
                original_value = row.get(k,0)
                log.debug('original value: ' + str(original_value))
                if type(original_value) == types.StringType or type(original_value) == types.UnicodeType:
                    for prop in properties.values():
                        log.debug('prop:'+str(prop))
                        prop_prop = prop['property']
                        # todo: WARN IF DATE IS OUTSIDE RANGE
                        
                        new_value = original_value.replace(u'$'+prop_prop, prop['value']) 
                        log.debug('new value:' + new_value)
                        try:
                            new_value = int(new_value)
                        except ValueError:
                        	 pass
                        original_value = new_value # sadly no better idea
                        #log.debug(str(original_value))                        
                        
                        
                row[k] = original_value
        
    @expose()
    @require(Any(is_user('user.erspl'), has_level('staff'), has_level('view'), msg='Only logged in users may view me properties'))
    def update_group_sheets(self, vgroup_id='', tag_sheet=None, eat_sheet=None, live_sheet=None, saveButton=''):
        # todo: accessor function making sure the type really is visiting_group
        visiting_group_o = holly_couch[vgroup_id] 
        
        if eat_sheet != None:
            vodb_eat_sheet = json.loads(eat_sheet)
            visiting_group_o['vodb_eat_sheet'] = vodb_eat_sheet
                        
            #...create cache content. Substitute properties and make sure we have at least zeros in all columns
            vodb_eat_computed = vodb_eat_sheet['items']            
            self.vodb_sheet_property_substitution(vodb_eat_computed, vodb_eat_times_options, visiting_group_o['visiting_group_properties'])
            
            visiting_group_o['vodb_eat_computed'] = vodb_eat_computed

        if live_sheet != None:
            vodb_live_sheet = json.loads(live_sheet)
            visiting_group_o['vodb_live_sheet'] = vodb_live_sheet
            vodb_live_computed = vodb_live_sheet['items']
            self.vodb_sheet_property_substitution(vodb_live_computed, vodb_live_times_options, visiting_group_o['visiting_group_properties'])
            visiting_group_o['vodb_live_computed'] = vodb_live_computed
              
            

        if tag_sheet != None:
            vodb_tag_sheet = json.loads(tag_sheet)
            visiting_group_o['vodb_tag_sheet'] = vodb_tag_sheet
            vodb_tag_computed = vodb_tag_sheet['items']
            vodb_tag_times_tags = self.compute_all_used_vgroup_tags(visiting_group_o['tags'], vodb_tag_sheet['items'])
            self.vodb_sheet_property_substitution(vodb_tag_computed, vodb_tag_times_tags, visiting_group_o['visiting_group_properties'])
            visiting_group_o['vodb_tag_computed'] = vodb_tag_computed
            	        
        holly_couch[vgroup_id] = visiting_group_o
        raise redirect(request.referrer)
        
        
        
    @expose('hollyrosa.templates.vodb_group_view')
    @require(Any(is_user('user.erspl'), has_level('staff'), has_level('view'), msg='Only logged in users may view me properties'))
    def view_vodb_group(self, visiting_group_id=''):
        visiting_group_o = holly_couch[visiting_group_id]
        
        #...construct the age group list. It's going to be a json document. Hard coded.
        #... if we are to partially load from database and check that we can process it, we do need to go from python to json. (and back)
        #...construct a program request template. It's going to be a json document. Hard coded.
        notes = [n.doc for n in getNotesForTarget(holly_couch, visiting_group_id)]
        
        visiting_group_o.show_vodb_live_sheet = json.dumps(dict(identifier='rid', items=visiting_group_o.get('vodb_live_computed', list())))
        visiting_group_o.show_vodb_eat_sheet = json.dumps(dict(identifier='rid', items=visiting_group_o.get('vodb_eat_computed', list())))
        visiting_group_o.show_vodb_tag_sheet = json.dumps(dict(identifier='rid', items=visiting_group_o.get('vodb_tag_computed', list())))

        
        tag_layout_tags = json.dumps(visiting_group_o['tags'])
        return dict(visiting_group=visiting_group_o, reFormatDate=reFormatDate, vodb_state_map=bokn_status_map, program_state_map=bokn_status_map, notes=notes, tag_layout_tags=tag_layout_tags)
        
        
        
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
            tmp_item['from_date'] = visiting_group_o['from_date']
            tmp_item['to_date'] = visiting_group_o['to_date']
        
        age_group_data = json.dumps(age_group_data_tmp)
        visiting_group_o.program_request_age_group = visiting_group_o.get('program_request_age_group', age_group_data)
        
        program_request_data_dict = {'identifier': 'id', 'items': [[{'id':0, 'requested_date': visiting_group_o['from_date'], 'requested_time':'', 'requested_activity': '', 'age_sma':False, 'age_spar':False, 'age_uppt':False, 'age_aven':False, 'age_utm':False, 'age_rov':False, 'age_led':False, 'note':''} for i in range(35)]] }
    
        
        
        program_request_data = json.dumps(program_request_data_dict)
        visiting_group_o.program_request = visiting_group_o.get('program_request', program_request_data)
        
        return dict(visiting_group_program_request=visiting_group_o, reFormatDate=reFormatDate, bokn_status_map=bokn_status_map)
        

        #
        # It would be a great step towards 2014 version with the improved 4-1 schedule view
        #
              
        #...raise...redirect referer...
        
    def fnCmpSortOnFromDate(self, a, b):
        return cmp(a['from_date'], b['from_date'])        
        
    
    def compute_used_dates_and_times(self, rows):
        used_dates = dict()
        used_times = dict()
        for row in rows:    
            used_dates[row.key[0]] = True
            used_times[row.key[1]] = True
        return used_dates, used_times
    
    @expose('hollyrosa.templates.vodb_group_booking_overview')
    @require(Any(is_user('user.erspl'), has_level('staff'), has_level('view'), has_level('vgroup'), msg=u'fff'))    
    def vodb_overview(self, compute_local_sum=False, compute_live=False):
        if compute_live:
            overview_live_o = getBookingOverview(holly_couch, None, None, reduce=False)
        else:
            overview_live_o = list()
        overview_eat_o = getBookingEatOverview(holly_couch, None, None, reduce=False)
        overview_value_map = dict()
        
        vodb_statuses = [-100, -10, 0, 5, 10, 20, 50]
        #used_dates = dict()
        #used_times = dict()
        used_vgroup_ids = dict()
        for tmp_status in vodb_statuses:
            used_vgroup_ids[tmp_status] = dict()
                       
        for row in list(overview_live_o) + list(overview_eat_o):
            #used_dates[row.key[0]] = True
            #used_times[row.key[1]] = True
            tmp_status = row.key[2]
            tmp_id = row.id
            if not used_vgroup_ids[tmp_status].has_key(tmp_id):             
                used_vgroup_ids[tmp_status][tmp_id] = holly_couch[tmp_id]
                
                
            overview_value_map['%s:%s:%s:%s' % (row.id, row.key[0], row.key[1], row.key[3])] = row.value
            if compute_local_sum:            
                try:
                    overview_value_map['%s:%s:%s:%s' % (row.id, row.key[0], row.key[1], 'SUM')] = overview_value_map.get('%s:%s:%s:%s' % (row.id, row.key[0], row.key[1], 'SUM'),0)+int(row.value)
                except ValueError:
                    pass
                except TypeError:
                    pass
                    
        used_dates, used_times = self.compute_used_dates_and_times(list(overview_live_o) + list(overview_eat_o))
            
        status_level_overview_o = getBookingOverview(holly_couch, None, None, reduce=True)
        status_level_eat_overview = getBookingEatOverview(holly_couch, None, None, reduce=True)
        #...copy paste!
        for row in list(status_level_overview_o) + list(status_level_eat_overview):
            tmp_status = row.key[2]
            tmp_id = 'sum.%d' % tmp_status
            log.debug('tmp_id='+str(tmp_id))
            if not used_vgroup_ids[tmp_status].has_key(tmp_id):
                tmp_o = DataContainer()
                tmp_o.id=tmp_id
                tmp_o.name='summa for %d' % tmp_status
                tmp_o.boknr=''
                tmp_o.from_date=''
                tmp_o.to_date=''
                tmp_o.vodbstatus = tmp_status
                tmp_o['from_date'] = '3000-00-00'

                used_vgroup_ids[tmp_status][tmp_id] = tmp_o
                
                
            overview_value_map['%s:%s:%s:%s' % (tmp_id, row.key[0], row.key[1], row.key[3])] = row.value
            if compute_local_sum:            
                try:
                    overview_value_map['%s:%s:%s:%s' % (tmp_id, row.key[0], row.key[1], 'SUM')] = overview_value_map.get('%s:%s:%s:%s' % (tmp_id, row.key[0], row.key[1], 'SUM'),0)+int(row.value)
                except ValueError:
                    pass

                
        #...build a list of dates, starting with headers 'status' and 'vgroup'
        if compute_live:
            times = vodb_live_times + vodb_eat_times
        else:
            times = vodb_eat_times
            
        header_block = [(t,1) for t in times] 
        header_block_len = len(header_block)        
        dates = used_dates.keys()
        dates.sort()
        header_dates = [(h, header_block_len) for h in dates]
        
        #...check if any date is missing
        #...add header to dates
        vgroup_header = [('status',1), ('group',1),('date',1),('opt',1)]                 
        header_dates = vgroup_header + header_dates
        
        header_times = used_times.keys()
        
        #...cheat.
        header_times = [('',1)] * len(vgroup_header) + header_block * len(used_dates.keys())
        date_colspan = len(header_block)
        
        if compute_local_sum:
            row_choices = vodb_live_times_options + ['SUM']
        else:
            row_choices = vodb_live_times_options
        row_span = len(row_choices)
        
        
        #..........................................................
        
        #...Each vgroup can be represented as
        #   [(status,4), (name,4), (refnr,4), (opt1,1) ]  + fm/inne + em/inne + kvall/inne + fru/inne + lu/inne + midd/inne + kvall/inne * dates
        vgroups = []
        
        for tmp_status in vodb_statuses:
            tmp_used_vgroups = used_vgroup_ids[tmp_status].values() 	
            tmp_used_vgroups.sort(self.fnCmpSortOnFromDate)
            for tmp_vgroup in tmp_used_vgroups:
                rowspan = len(row_choices)
                for tmp_opt in row_choices:
                    date_opts = []
                    for d in dates:
                        for t in times:
                            if tmp_opt not in ['fm','em','evening']:
                                if t == 'daytrip':
                                    t = 'own'
                            date_opts.append('%s:%s:%s:%s' % (tmp_vgroup.id, d, t, tmp_opt))                       
                    #date_opts = ['%s:%s:%s:%s' % (tmp_vgroup.id, d, t, tmp_opt) for d in dates for t in times]
                    vgroups.append(  (tmp_vgroup, tmp_opt, date_opts, rowspan )  )
                    
                    if rowspan > 1:
                        rowspan=0                    
                    
            
        return dict(header_dates=header_dates, header_times=header_times, row_choices=row_choices, vgroup_opts=vgroups, values=overview_value_map)
   
        
    def fn_cmp_vgroups_on_date(self, a, b):
        return cmp(a['from_date'], b['from_date'])

    
    def getVisitingGroupIdsOfViewSet(self, rows):
        vgroup_ids = dict()
        for row in rows:
            vgroup_ids[row.id] = True
        return vgroup_ids
        
    
    def makeSummaryVGroups(self, a_options, a_vodb_status_map):
        summary_vgroups = dict()
        for live_option in a_options:
            for vodb_status, vodb_status_name in a_vodb_status_map.items():
                try:
                    summary_live_option_vgroups = summary_vgroups[live_option]
                except KeyError:
                    summary_vgroups[live_option] = dict()
                    summary_live_option_vgroups = summary_vgroups[live_option]	            
                summary_live_option_vgroups[vodb_status] = DataContainer(id='summary_%s_%d' % (live_option, vodb_status), name=vodb_status_name, vodbstatus=vodb_status, from_date='', to_date='', vodb_live_computed=list(), has_values=False, all_values_zero=True)
        return summary_vgroups
        
        
    def computeDateRangeOfSummaryVGroup(self, a_summary_vgroups, a_vodb_live_times_options, a_vodb_status_map):
        """
        now that we have populated the dict-dict, we need to compute the date-range.
        """
        for live_option in a_vodb_live_times_options:
            for vodb_status, vodb_status_name in a_vodb_status_map.items():
                summary_live_option_vgroups = a_summary_vgroups[live_option]
                tmp_summary_group = summary_live_option_vgroups[vodb_status]
                if not tmp_summary_group.has_values:
                    formated_dates = []
                else:
                    formated_dates = dateRange(tmp_summary_group['from_date'], tmp_summary_group['to_date'], format='%Y-%m-%d')
                tmp_summary_group.date_range = formated_dates
    
    def computeLiveSummaries(self, a_live_summaries_rows, a_summary_vgroups):
        """iterating through reduced result set should give the data we need. """  
        for live_computed_summary in a_live_summaries_rows:      
            tmp_date = live_computed_summary.key[0]
            tmp_time = live_computed_summary.key[1]
            tmp_status = live_computed_summary.key[2]
            tmp_option = live_computed_summary.key[3]
            tmp_value = live_computed_summary.value
            
            #...            
            summary_vgroup = a_summary_vgroups[tmp_option][tmp_status]
            if summary_vgroup.from_date > tmp_date or summary_vgroup.from_date=='':
                summary_vgroup.from_date = tmp_date
                summary_vgroup.has_values = True
            if summary_vgroup.to_date < tmp_date or summary_vgroup.to_date=='':
                summary_vgroup.to_date = tmp_date
                summary_vgroup.has_values = True
                
            #...append data to the vodb_live_computed list assuming all data in order this should work BUT we might get a hole in our data set (not good)
            try:
                tmp_live_summary_dict = summary_vgroup['live_summary']
            except:
                summary_vgroup.live_summary = dict()
                tmp_live_summary_dict = summary_vgroup['live_summary']

            
            tmp_live_summary_dict[tmp_date+':'+tmp_time] = tmp_value
            if tmp_value != '0':
                summary_vgroup.all_values_zero = False
                
                
    def getCompKey(self, a_vodb_status, a_live_row):
        return "%s:%s:%s" % (a_vodb_status, a_live_row['date'], a_live_row['time'])
        
        
    @expose('hollyrosa.templates.vodb_group_booking_overview2')
    @require(Any(is_user('user.erspl'), has_level('staff'), has_level('view'), has_level('vgroup'), msg=u'fff'))    
    def vodb_booking_overview2(self, compute_local_sum=False, compute_live=False):
        # the aim at first is to start draw grid / sheet using div tags instead of a table.
        overview_live_o = getBookingOverview(holly_couch, None, None, reduce=False)
        used_dates, used_times = self.compute_used_dates_and_times(overview_live_o)
        used_dates_keys = used_dates.keys()
        used_dates_keys.sort()
        header_dates = used_dates_keys
        header_times = used_times.keys()
        
        #cheat
        header_times = ['fm','em','evening']
        
        #...computing the vgroups we are looking for
        vgroup_ids = self.getVisitingGroupIdsOfViewSet(overview_live_o) #dict()
        #for row in overview_live_o:
        #    vgroup_ids[row.id] = True
            
        
        #...create booking for all summary groups
        summary_vgroups = self.makeSummaryVGroups(vodb_live_times_options, vodb_status_map) #dict()
        #for live_option in vodb_live_times_options:
        #    log.debug('live_option: '+ live_option)
        #    for vodb_status, vodb_status_name in vodb_status_map.items():
        #        try:
        #            summary_live_option_vgroups = summary_vgroups[live_option]
        #        except KeyError:
        #            summary_vgroups[live_option] = dict()
        #            summary_live_option_vgroups = summary_vgroups[live_option]	
        #        
        #            
        #            
        #        summary_live_option_vgroups[vodb_status] = DataContainer(id='summary_%s_%d' % (live_option, vodb_status), name=vodb_status_name, vodbstatus=vodb_status, from_date='', to_date='', vodb_live_computed=list())
        
        
        #...iterating through reduced result set should give the data we need  
        live_summaries_rows = getBookingOverview(holly_couch, None, None, reduce=True)
        self.computeLiveSummaries(live_summaries_rows, summary_vgroups)
        #for live_computed_summary in live_computed_summarys:      
        #    tmp_date = live_computed_summary.key[0]
        #    tmp_time = live_computed_summary.key[1]
        #    tmp_status = live_computed_summary.key[2]
        #    tmp_option = live_computed_summary.key[3]
        #    tmp_value = live_computed_summary.value
        #    
        #    #...            
        #    summary_vgroup = summary_vgroups[tmp_option][tmp_status]
        #    if summary_vgroup.from_date > tmp_date or summary_vgroup.from_date=='':
        #        summary_vgroup.from_date = tmp_date
        #        summary_vgroup.has_values = True
        #    if summary_vgroup.to_date < tmp_date or summary_vgroup.to_date=='':
        #       summary_vgroup.to_date = tmp_date
        #       summary_vgroup.has_values = True
        #        
        #    #...append data to the vodb_live_computed list assuming all data in order this should work BUT we might get a hole in our data set (not good)
        #    try:
        #        tmp_live_summary_dict = summary_vgroup['live_summary']
        #    except:
        #        summary_vgroup.live_summary = dict()
        #        tmp_live_summary_dict = summary_vgroup['live_summary']
        #
        #    
        #    tmp_live_summary_dict[tmp_date+':'+tmp_time] = tmp_value
        #    if tmp_value != '0':
        #        summary_vgroup.all_values_zero = False
            
        
        #...now that we have populated the dict-dict, we need to compute the date-range
        self.computeDateRangeOfSummaryVGroup(summary_vgroups, vodb_live_times_options, vodb_status_map)  
        #for live_option in vodb_live_times_options:
        #    for vodb_status, vodb_status_name in vodb_status_map.items():
        #        summary_live_option_vgroups = summary_vgroups[live_option]
        #        tmp_summary_group = summary_live_option_vgroups[vodb_status]
        #        if not tmp_summary_group.has_values:
        #            formated_dates = []
        #        else:
        #            formated_dates = dateRange(tmp_summary_group['from_date'], tmp_summary_group['to_date'], format='%Y-%m-%d')
        #        tmp_summary_group.date_range = formated_dates
        #    
            
        vgroups = list()
        for tmp_id in vgroup_ids.keys():
            tmp_vgroup = holly_couch[tmp_id]
            formated_dates = dateRange(tmp_vgroup['from_date'], tmp_vgroup['to_date'], format='%Y-%m-%d')
            tmp_vgroup['date_range'] = formated_dates
            
            live_computed_by_date = dict()
            for tmp_live_row in tmp_vgroup['vodb_live_computed']:
                for k in ['indoor','outdoor','daytrip']:
                    tmp_comp_key = self.getCompKey(k, tmp_live_row)
                    live_computed_by_date[tmp_comp_key] = tmp_live_row[k]
            tmp_vgroup['live_computed_by_date'] =  live_computed_by_date           
            vgroups.append(tmp_vgroup)
        
        vgroups.sort(self.fn_cmp_vgroups_on_date)
        
        
        
        return dict(header_dates=header_dates, header_times=header_times, vgroups=vgroups, bokn_status_map=bokn_status_map, vodb_status_map=vodb_status_map, summary_vgroups=summary_vgroups)