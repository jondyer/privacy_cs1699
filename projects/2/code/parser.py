#####################################################################
# Jonathan Dyer
# CS1699: Privacy in the Electronic Society
# Project 2
# 6 April 2018
#
# File:     parser.py
# Usage:    python parser.py [policyfile]
#           Run with valid policy file or with no args to get prompt
#           (run in same directory as policy file for best results)
# Purpose:  This is the parser/preprocessor/access control
#           interpreting program for the RT variant defined in
#           the jondyer_p2.pdf document.
#
#           Tested using Python 2.7 and Python 3.5 -- it is not very
#           robust, so don't go typing random values ;) It also
#           depends on the policy file being well-formed, so be sure
#           to read the document mentioned above.
#####################################################################
import sys
import xml.etree.ElementTree as ET

#-----------------------------------------------------------
# Some auxiliary functions for debugging/helpfulness:
#-----------------------------------------------------------
def heading(str):
    print('-'*60)
    print("** %s:" % (str,))
    print('-'*60)

def print_rows(rows):
    for row in rows:
        print(row)

#------------------------------------------------------------
# show_menu
#------------------------------------------------------------
def show_menu():
    menu = '''
--------------------------------------------------
1. List objects
2. List groups
---
3. List roles
4. List subjects
---
5. Make an access query


Choose (1-7, 0 to quit): '''

    try:
        choice = int(input( menu ))
    except ValueError:
        print("\n\n* Invalid choice. Choose again.")
        show_menu()
    else:
        if choice == 0:
            print('Done.')
            exit(0)
        elif choice in range(1,1+4):
            e = get_entity_menu()
            actions[choice](e)
            show_menu()
        elif choice == 5:
            if actions[choice]():
                print('\n\nAllow')
            else:
                print('\n\nDeny')
            show_menu()
        else:
            print("\n\n* Invalid choice (%s). Choose again." % choice)
            show_menu()
    finally:
        None


#------------------------------------------------------------
# get_entity_menu
#------------------------------------------------------------
def get_entity_menu():
    menu_1 = '''
--------------------------------------------------
Please select an entity:
'''
    menu_2 = '''
Choose a value (0 to exit): '''
    try:
        print( menu_1 )
        i = 1
        for x in ents:
            n = x.get('name')
            print('{0:2d}: {1}'.format(i, n))
            i += 1

        choice = int(input( menu_2 ))
    except ValueError:
        print("\n\n* Invalid choice. Choose again.")
        return get_entity_menu()
    else:
        if choice == 0:
            print('Done.')
            exit(0)
        elif choice in range(1,1+i):
            node = ents[choice-1].get('name')
            return all_ents[node]
        else:
            print("\n\n* Invalid choice (%s). Choose again." % choice)
            return get_entity_menu()
    finally:
        None


#-----------------------------------------------------------
# Now let's really have some fun.
# This class will hold all relevant info about an entity for us.
#-----------------------------------------------------------
class Entity:
    ########################## BEGIN PARSING AND INITIALIZATION ####################################
    def __init__(self, root):          # root should be the entity node

        self.objects = {}               # maps name of object => <object> node
        self.obj_with_groups = {}       # maps object name => set (names of groups)
        self.objectGroups = {}          # maps group name => set {names of objects in group}
        self.roles = {}                 # maps name of role => <role> node
        self.role_rights = {}           # maps (role name, access type) => set {names of objects affected}
        self.subjects = {}              # maps name of subject => <subject> node
        self.subj_roles = {}            # maps subject name => set {names of roles}
        self.delegated1 = False         # flag to indicate whether importing roles has taken place
        self.delegated2 = False         # flag to indicate whether importing roles has taken place


        self.name = root.get('name')    # set the name of the entity
        data = root.find('data')

        # First deal with objects
        objects = data.find('objects')
        object_array = objects.findall('object')       # this arr holds all objects for this ent
        objGp_array = objects.findall('objectGroup')

        for o in objGp_array:           # add all object groups to hash by name => []
            n = o.find('name').text
            self.objectGroups[n] = set()

        for o in object_array:                      # for each object in the entity
            n = o.find('name').text
            self.objects[n] = o                     # map standard objects hash
            self.obj_with_groups[n] = set()
            gs = o.findall('group')

            for g in gs:                            # for each group the object is in
                d = g.text                              # extract group name
                self.obj_with_groups[n].add(d)          # add group to set
                self.objectGroups[d].add(n)             # update group name => object hash


        # Then deal with roles
        roles = data.find('roles')
        role_array = roles.findall('role')

        for r in role_array:                        # for each role in the entity
            n = r.find('name').text
            self.roles[n] = r                           # map the standard roles hash

            for p in r.findall('permission'):           # for each permission in the role
                ty = p.find('type').text                    # get the type of permission
                tu = (n,ty)
                self.role_rights[tu] = set()                # map (role,type) => empty set

                for t in p.findall('target'):               # for each target in this permission
                    if t.get('type') == 'object':               # if it's an object
                        self.role_rights[tu].add(t.text)        # add it to the (role,type) set
                    elif t.get('type') == 'objectGroup':        # else it's an objectGroup, add all
                        self.role_rights[tu].update(self.objectGroups[t.text])
                # finish all targets in the permission
            # finish all permissions in the role
        # finish all roles in the entity


        # Finally subjects
        subjects = data.find('subjects')
        subj_array = subjects.findall('subject')

        for s in subj_array:
            n = s.find('name').text
            self.subjects[n] = s
            su = s.findall('role')
            self.subj_roles[n] = set()

            for sr in su:
                self.subj_roles[n].add(sr.text)
            # finish all roles for this subject
        # finish all subjects in the entity


        # Now for policies!
        policies = root.find('policies')

        # First hierarchy
        hi = policies.findall('hierarchy')
        for h in hi:                            # for each hierarchy
            i = h.find('if').text                  # extract the 'if' role
            t = h.find('then').text                 # extract the 'then' role

            for s in self.subjects:                 # for each subject
                if i in self.subj_roles[s]:             # if role goes with subject
                    self.subj_roles[s].add(t)           # then add the new role

            for rr in self.role_rights:             # also for each role-right combo
                r,ty = rr                               # extract role, type info
                if t == r:                              # if the role is the 'then' role
                    tu = (i,ty)                             # then its rights belong to 'if'!
                    self.role_rights[tu].update(self.role_rights[rr])

        # Now inference
        infer = policies.findall('inference')
        for inf in infer:                       # for each inference
            i = inf.find('if').text                # extract the 'if' group
            t = inf.find('then').text               # extract the 'then' group

            for o in self.objects:                  # for each object
                if i in self.obj_with_groups[o]:        # if group goes with object
                    self.obj_with_groups[o].add(t)      # then add new group
                    self.objectGroups[t].add(o)         # and add object to new group

        # Finally delegation -- stored for now, then dealt with in a method
        self.deleg = policies.findall('delegation')

    def delegate(self):
        if self.delegated1:
            self.delegated2 = True
        elif self.delegated2:
            return

        for duh in self.deleg:
            i = duh.find('if').text                 # extract the 'if' role
            t = duh.find('then').text               # extract the 'then' role
            fr = duh.find('from').text              # extract 'from' entity
            to = duh.find('to').text                # extract 'to' entity

            if to != self.name:                     # skip if 'to' not this entity
                continue

            if not all_ents[fr].delegated1:
                all_ents[fr].delegate()

            for s in self.subjects:                     # for each subject here
                if s in all_ents[fr].subjects:       # if subject exists in 'from' entity    ???
                    if i in all_ents[fr].subj_roles[s]:         # if 'if' role goes with subject there
                        self.subj_roles[s].add(t)               # then add 'then' role here ('to')


        self.delegated1 = True
    ############################## END PARSING AND INITIALIZATION ##################################


    def l_objects(self):
        return self.obj_with_groups

    def l_groups(self):
        return self.objectGroups

    def l_roles(self):
        return self.role_rights

    def l_subjects(self):
        return self.subj_roles

    # TODO: Provide option to print out policies (EASY) 

#------------------------------------------------------------
# list_objects
#------------------------------------------------------------
def list_objects_menu(entity):
    heading('List Objects')

    for name, gps_set in entity.l_objects().items():
        print('\nName:   {0}\nGroups: {1}'.format(name, list(gps_set)))


#------------------------------------------------------------
# list_object_groups
#------------------------------------------------------------
def list_groups_menu(entity):
    heading('List Groups')

    for gp, obj_set in entity.l_groups().items():
        print('\nGroup:   {0}\nObjects: {1}'.format(gp, list(obj_set)))


#------------------------------------------------------------
# list_roles
#------------------------------------------------------------
def list_roles_menu(entity):
    heading('List Roles')

    # TODO: Change this so it prints each role at once -- may have to switch to nested dicts
    for tup, obj_set in entity.l_roles().items():
        name, access = tup
        print('\nName:    {0}\nAccess:  {1}\nObjects: {2}'.format(name, access, list(obj_set)))


    # for row in rows:
    #     id, first, last, email = row
    #     print("%s. %s, %s (%s)" % (id, last, first, email))

#------------------------------------------------------------
# list_subjects
#------------------------------------------------------------
def list_subjects_menu(entity):
    heading('List Subjects')

    for name, sub_set in entity.l_subjects().items():
        print('\nSubject: {0}\nRoles:   {1}'.format(name, list(sub_set)))


#-----------------------------------------------------------------
# access_query
#-----------------------------------------------------------------

def access_query():
    heading('Access Query')

    try:
        print('Can user U access file F with privilege P?\nAll inputs are case-sensitive!\n')
        user = str(input( 'Please enter the subject (user) name: ' ))
        resource = str(input( 'Please enter the object (file) name: '))
        access = str(input( 'Please enter the type of access (privilege): '))
    except ValueError:
        print("\n\n* Invalid choice. Choose again.")
        return access_query()
    else:
        for e, e_obj in all_ents.items():                           # for any entity
            if resource in e_obj.objects and user in e_obj.subjects:    # if both the object and subject exist there
                for role in e_obj.roles:                                    # for all roles there
                    if resource in e_obj.role_rights[(role,access)]:            # if the role has that permission for the object
                        if role in e_obj.subj_roles[user]:                          # and the user has that role
                            return True                                                 # then we're good to go
        return False
    finally:
        None


# We leverage the fact that in Python functions are first class
# objects and build a dictionary of functions numerically indexed

actions = { 1:list_objects_menu,    2:list_groups_menu,   3:list_roles_menu,
            4:list_subjects_menu,  5:access_query }


if __name__ == '__main__':
    try:
        if len(sys.argv) >=2:       # command-line usage
            f = sys.argv[1]
        else:
            f = str(input("Please enter the relative filepath: "))
        tree = ET.parse(f)
        root = tree.getroot()
        ents = root.findall("*")    # this is a list of entity nodes

        # we want the entity objects to be globally available, so create them here
        all_ents = {}               # this is a hash of entity names => objects
        for e in ents:
            e_obj = Entity(e)
            all_ents[e_obj.name] = e_obj

        # now because delegation requires that other entities be formed already, we
        # must wait until after the loop to update any permissions according to delegation
        for e in all_ents.values():
            e.delegate()

        show_menu()


    except IOError as e:
        print("Error: %s" % (e,))
