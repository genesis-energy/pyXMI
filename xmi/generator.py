#!/usr/bin/python
import sys
import os
import json
import yaml

from lxml import etree
from jinja2 import Template, Environment, FileSystemLoader

from xmi.uml.parse import ns, parse_uml, UMLPackage, UMLClass, UMLAttribute

from xmi.validator import validate_package, validate_test_cases

settings = None


def output_model(package, recipie_path):
    env = Environment(loader=FileSystemLoader(settings['templates_folder']))
    for template_definition in settings['templates']:
        template = env.get_template(template_definition['source'])
        filename_template = Template(template_definition['dest'])
        filter_template = None
        if 'filter' in template_definition.keys():
            filter_template = Template(template_definition['filter'])

        if template_definition['level'] == 'package':
            if filter_template is None or filter_template.render(package=package) == "True":
                filename = os.path.abspath(filename_template.render(package=package))
                dirname = os.path.dirname(filename)
                if not os.path.exists(dirname):
                    os.makedirs(dirname)
                # print("Writing: " + filename)
                with open(filename, 'w') as fh:
                    fh.write(template.render(package=package))

        elif template_definition['level'] == 'class':
            for cls in package.classes:

                if filter_template is None or filter_template.render(cls=cls) == "True":
                    filename = os.path.abspath(filename_template.render(cls=cls))
                    dirname = os.path.dirname(filename)
                    if not os.path.exists(dirname):
                        os.makedirs(dirname)
                    # print("Writing: " + filename)
                    with open(filename, 'w') as fh:
                        fh.write(template.render(cls=cls))

        elif template_definition['level'] == 'enumeration':
            for enum in package.enumerations:

                if filter_template is None or filter_template.render(enum=enum) == "True":
                    filename = os.path.abspath(filename_template.render(enum=enum))
                    dirname = os.path.dirname(filename)
                    if not os.path.exists(dirname):
                        os.makedirs(dirname)
                    # print("Writing: " + filename)
                    with open(filename, 'w') as fh:
                        fh.write(template.render(enum=enum))

        elif template_definition['level'] == 'assocication':
            for assoc in package.associations:

                if filter_template is None or filter_template.render(association=assoc) == "True":
                    filename = os.path.abspath(filename_template.render(association=assoc))
                    dirname = os.path.dirname(filename)
                    if not os.path.exists(dirname):
                        os.makedirs(dirname)
                    # print("Writing: " + filename)
                    with open(filename, 'w') as fh:
                        fh.write(template.render(association=assoc))

    for child in package.children:
        output_model(child, recipie_path)


def output_test_cases(test_cases):
    print("Generating test case output")
    for case in test_cases:
        serialised = json.dumps(serialize_instance(case), indent=2)

        for template_definition in settings['test_templates']:
            filename_template = Template(template_definition['dest'])
            filename = os.path.abspath(filename_template.render(ins=case))
            dirname = os.path.dirname(filename)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            # print("Writing: " + filename)
            with open(filename, 'w') as fh:
                fh.write(serialised)


def serialize_instance(instance):
    ret = {}

    for attr in instance.attributes:
        ret[attr.name] = attr.value

    # for assoc in instance.associations_to:
    #    if assoc.source_multiplicity[1] == '*':
    #        if assoc.source.name not in ret.keys():
    #            ret[assoc.source.name] = [serialize_instance(assoc.source),]
    #        else:
    #            ret[assoc.source.name].append(serialize_instance(assoc.source))
    #    else:
    #            ret[assoc.source.name] = serialize_instance(assoc.source)

    for assoc in instance.associations_from:
        if assoc.dest_multiplicity[1] == '*':
            if assoc.dest.name not in ret.keys():
                ret[assoc.dest.name] = [serialize_instance(assoc.dest), ]
            else:
                ret[assoc.dest.name].append(serialize_instance(assoc.dest))
        else:
            ret[assoc.dest.name] = serialize_instance(assoc.dest)

    return ret


def parse(recipie_path, settings):
    tree = etree.parse(settings['source'])

    # Check that we have the right XMI version
    root = tree.getroot()
    if root is None:
        raise ValueError('Not a valid XMI')
    version = root.get('{%s}version' % ns['xmi'])
    if version is None:
        raise ValueError('No XMI version specified')
    elif version != "2.1":
        raise ValueError('XMI version must be 2.1')
    model = tree.find('uml:Model', ns)
    if model is None:
        raise ValueError("Could not find model, UML version must be 2.1")

    root_package = model.xpath("//packagedElement[@name='%s']" % settings['root_package'], namespaces=ns)
    if len(root_package) == 0:
        print("Root packaged element not found. Settings has:{}".format(settings['root_package']))
        return
    root_package = root_package[0]

    model_package, test_cases = parse_uml(root_package, tree)
    print("Base Model Package: " + model_package.name)
    return model_package, test_cases


def validate(model_package, test_cases, settings):

    print("Validating parsed model")
    errors = validate_package(model_package, settings)

    print("Validating test data")
    for case in test_cases:
        errors += validate_test_cases(case, settings)

    if len(errors) > 0:
        print("Validation Errors:")
        for error in errors:
            print("    {}".format(error))


def generate(model_package, test_cases, recipie_path ):
    print("Generating model output")
    output_model(model_package, recipie_path)
    output_test_cases(test_cases)


def run(recipie_path):
    global settings

    config_filename = recipie_path + "/config.yaml"
    os.environ.setdefault("PYXMI_SETTINGS_MODULE", config_filename)

    with open(config_filename, 'r') as config_file:
        settings = yaml.load(config_file.read(), Loader=yaml.SafeLoader)

    model_package, test_cases = parse(recipie_path, settings)
    validate( model_package, test_cases, settings )
    generate( model_package, test_cases, recipie_path )