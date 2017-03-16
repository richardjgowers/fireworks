__author__ = 'Ivan Kondov'
__email__ = 'ivan.kondov@kit.edu'
__copyright__ = 'Copyright 2016, Karlsruhe Institute of Technology'

from fireworks import Firework
from fireworks.core.firework import FWAction, FireTaskBase
from fireworks.utilities.fw_utilities import explicit_serialize


class SingleTask(FireTaskBase):
    __doc__ = """
        This firetask passes 'inputs' to a specified python function and
        stores the 'outputs' to the spec of the current firework and the 
        next firework using FWAction.
    """
    _fw_name = 'SingleTask'
    required_params = ['function']
    optional_params = ['inputs', 'outputs', 'current']

    def run_task(self, fw_spec):
        node_input = self.get('inputs')
        node_output = self.get('outputs')

        inputs = []
        if type(node_input) in [str, unicode]:
            inputs.append(fw_spec[node_input])
        elif type(node_input) is list:
            for item in node_input:
                inputs.append(fw_spec[item])
        elif node_input is not None:
            raise TypeError('input must be a string or a list')

        foo, bar = self['function'].split('.',2)
        func = getattr(__import__(foo), bar)
        outputs = func(*inputs)

        if node_output is None:
            return FWAction()

        if type(outputs) == tuple:
            if type(node_output) == list:
                output_dict = {}
                for (index, item) in enumerate(node_output):
                    output_dict[item] = outputs[index]
            else:
                output_dict = {node_output: outputs}
            return FWAction(stored_data=output_dict, update_spec=output_dict)
        else: # list, dict, str, int, float, ...
            if self.get('current') is not None:
                return FWAction(
                    stored_data={node_output: outputs},
                    mod_spec=[{'_push': {node_output: outputs}}])
            else:
                return FWAction(
                    stored_data={node_output: outputs},
                    update_spec={node_output: outputs})


class ForeachTask(FireTaskBase):
    __doc__ = """
        This firetask branches the workflow creating parallel fireworks 
        using FWAction: one firework for each element in 'split' list.
    """
    _fw_name = 'ForeachTask'
    required_params = ['function', 'split', 'inputs']
    optional_params = ['outputs']

    def run_task(self, fw_spec):
        split_input = self['split']
        node_input = self['inputs']
        if type(split_input) not in [str, unicode]:
            raise TypeError('the "split" argument must be a string')
        if type(fw_spec[split_input]) is not list:
            raise TypeError('the "split" argument must point to a list')
        if type(node_input) is list:
            if split_input not in node_input:
                raise ValueError('the "split" argument must be in argument list')
        else:
            if split_input != node_input:
                raise ValueError('the "split" argument must be in argument list')

        number = len(fw_spec[split_input])
        if number < 1:
            print(self._fw_name, 'error: input to split is empty:', split_input)
            return FWAction(defuse_workflow=True)

        fireworks = []
        for index in range(number):
            spec = fw_spec.copy()
            spec[split_input] = spec[split_input][index]
            fireworks.append(
                Firework(
                    SingleTask(
                        function = self['function'],
                        inputs = node_input,
                        outputs = self.get('outputs'), 
                        current = index
                    ),
                    spec = spec,
                    name=self._fw_name + ' ' + str(index)
                )
            )
        return FWAction(detours = fireworks)


class JoinDictTask(FireTaskBase):
    """
        This firetask combines specified spec fields into a new dictionary
    """
    _fw_name = 'JoinDictTask'
    required_params = ['inputs', 'outputs']
    optional_params = ['rename']

    def run_task(self, fw_spec):

        if type(self['outputs']) not in [str, unicode]:
            raise TypeError('"outputs" must be a single string item')

        if self['outputs'] not in fw_spec.keys():
            outputs = {}
        elif type(fw_spec[self['outputs']]) is dict:
            outputs = fw_spec[self['outputs']]
        else:
            raise TypeError('"outputs" exists but is not a dictionary')

        for item in self['inputs']:
            if self.get('rename') and item in self['rename']:
                outputs[self['rename'][item]] = fw_spec[item]
            else:
                outputs[item] = fw_spec[item]

        return FWAction(
            stored_data={self['outputs']: outputs},
            update_spec={self['outputs']: outputs})


class JoinListTask(FireTaskBase):
    """
        This firetask combines specified spec fields into a new list
    """
    _fw_name = 'JoinListTask'
    required_params = ['inputs', 'outputs']

    def run_task(self, fw_spec):

        if type(self['outputs']) not in [str, unicode]:
            raise TypeError('"outputs" must be a single string item')
            
        if self['outputs'] not in fw_spec.keys():
            outputs = []
        elif type(fw_spec[self['outputs']]) is list:
            outputs = fw_spec[self['outputs']]
        else:
            raise TypeError('"outputs" exists but is not a list')

        for item in self['inputs']:
            outputs.append(fw_spec[item])

        return FWAction(
            stored_data={self['outputs']: outputs},
            update_spec={self['outputs']: outputs})


