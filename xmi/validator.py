#!/usr/bin/python
import sys
import os
import json
import yaml

from lxml import etree
from jinja2 import Template, Environment, FileSystemLoader

from xmi.uml.parse import ns, parse_uml, UMLPackage, UMLClass, UMLAttribute

settings = None


class ClassValidationError(object):
    def __init__(self, package, cls, error):
        self.package = package
        self.error = error
        self.cls = cls
        
    def __repr__(self):
        return "Class error: {}{} | {}".format(self.package.path, self.cls.name, self.error)


class AttributeValidationError(object):
    def __init__(self, package, cls, attr, error):
        self.package = package
        self.error = error
        self.cls = cls
        self.attr = attr
        
    def __repr__(self):
        return "Attribute error: {}{}.{} | {}".format(self.package.path, self.cls.name, self.attr.name, self.error)


def validate_package(package,settings):
    errors = []
    
    for cls in package.classes:
        if not hasattr(cls,'domain'):
            errors.append( ClassValidationError(package,cls,"Class does not belong to a domain") )
    
        if cls.id_attribute == None and cls.is_abstract == False:
            if cls.supertype == None or cls.supertype.id_attribute == None:
                errors.append( ClassValidationError(package,cls,"no primary key") )
        elif cls.supertype != None:
            if cls.supertype.id_attribute != None and cls.id_attribute != cls.supertype.id_attribute:
                errors.append( ClassValidationError(package,cls,"To allow polymorphism the primary key must be defined in only the supertype") )

        has_id = False
        for attr in cls.attributes:
            if attr.stereotype == "auto" and attr.type != "int":
                errors.append( AttributeValidationError(package,cls,attr,"auto increment field must be int") )

            if attr.classification == None and attr.type not in settings['types'].keys():
                errors.append( AttributeValidationError(package,cls,attr,"unknown type: {}".format(attr.type)) )
                
            if attr.is_id == True:
                if has_id == True:
                    errors.append( AttributeValidationError(package,cls,attr,"multiple ID attributes detected") )
                has_id = True
                
            if attr.name == 'is_deleted':
                errors.append( AttributeValidationError(package,cls,attr,"is_deleted is a reserved attribute name") )
            
    for child in package.children:
        errors += validate_package(child,settings)
        
    return errors


def validate(recipie_path):
    global settings
    
    config_filename = recipie_path+"/config.yaml"
    os.environ.setdefault("PYXMI_SETTINGS_MODULE", config_filename )

    with open(config_filename, 'r') as config_file:
        settings=yaml.load(config_file.read(), Loader=yaml.SafeLoader)

    tree = etree.parse(settings['source'])
    model=tree.find('uml:Model',ns)
    root_package=model.xpath("//packagedElement[@name='%s']"%settings['root_package'], namespaces=ns)
    if len(root_package) == 0:
        print("Root packaged element not found. Settings has:{}".format(settings['root_package']))
        return
    root_package=root_package[0]
    
    extension=tree.find('xmi:Extension',ns)

    model_package, test_cases = parse_uml(root_package, tree)
    
    # validations
    # Does each object have a primary key
    # Do objects with primary keys have a parent class which also has a primary key
    # Are all auto increment fields int
    print(validate_package(model_package,settings))
    
    # Does each class have a domain
    # Are there unexpected attribute types