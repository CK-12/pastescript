from __future__ import print_function
# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
import os
import re
from importlib.metadata import distribution, entry_points, PackageNotFoundError

def add_plugin(egg_info_dir, plugin_name):
    """
    Add the plugin to the given distribution (or spec), in
    .egg-info/paster_plugins.txt
    """
    fn = os.path.join(egg_info_dir, 'paster_plugins.txt')
    if not os.path.exists(fn):
        lines = []
    else:
        f = open(fn)
        lines = [l.strip() for l in f.readlines() if l.strip()]
        f.close()
    if plugin_name in lines:
        # Nothing to do
        return
    lines.append(plugin_name)
    if not os.path.exists(os.path.dirname(fn)):
        os.makedirs(os.path.dirname(fn))
    f = open(fn, 'w')
    for line in lines:
        f.write(line)
        f.write('\n')
    f.close()

def remove_plugin(egg_info_dir, plugin_name):
    """
    Remove the plugin to the given distribution (or spec), in
    .egg-info/paster_plugins.txt.  Raises ValueError if the
    plugin is not in the file.
    """
    fn = os.path.join(egg_info_dir, 'paster_plugins.txt')
    if not os.path.exists(fn):
        raise ValueError(
            "Cannot remove plugin from %s; file does not exist"
            % fn)
    f = open(fn)
    lines = [l.strip() for l in f.readlines() if l.strip()]
    f.close()
    for line in lines:
        # What about version specs?
        if line.lower() == plugin_name.lower():
            break
    else:
        raise ValueError(
            "Plugin %s not found in file %s (from: %s)"
            % (plugin_name, fn, lines))
    lines.remove(line)
    print('writing', lines)
    f = open(fn, 'w')
    for line in lines:
        f.write(line)
        f.write('\n')
    f.close()

def find_egg_info_dir(dir):
    while 1:
        try:
            filenames = os.listdir(dir)
        except OSError:
            # Probably permission denied or something
            return None
        for fn in filenames:
            if (fn.endswith('.egg-info')
                and os.path.isdir(os.path.join(dir, fn))):
                return os.path.join(dir, fn)
        parent = os.path.dirname(dir)
        if parent == dir:
            # Top-most directory
            return None
        dir = parent

def resolve_plugins(plugin_list):
    found = []
    while plugin_list:
        plugin = plugin_list.pop()
        try:
            dist = distribution(plugin)
        except PackageNotFoundError as e:
            msg = '%sNot Found%s: %s (did you run python setup.py develop?)'
            if str(e) != plugin:
                e.args = (msg % (str(e) + ': ', ' for', plugin)),
            else:
                e.args = (msg % ('', '', plugin)),
            raise
        found.append(plugin)
        if dist.metadata.get('Metadata-Version'):
            try:
                data = dist.read_text('paster_plugins.txt')
                if data:
                    for add_plugin in parse_lines(data):
                        if add_plugin not in found:
                            plugin_list.append(add_plugin)
            except (FileNotFoundError, KeyError):
                pass
    return list(map(get_distro, found))

def get_distro(spec):
    return distribution(spec)

def load_commands_from_plugins(plugins):
    commands = {}
    for dist in plugins:
        # dist is already a Distribution object from resolve_plugins()
        try:
            # Get entry points from this specific distribution's metadata
            dist_entry_points = dist.entry_points
            for ep in dist_entry_points:
                if ep.group == 'paste.paster_command':
                    commands[ep.name] = ep
        except (AttributeError, FileNotFoundError):
            # If we can't read entry points from the distribution, skip it
            pass
    return commands

def parse_lines(data):
    result = []
    for line in data.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            result.append(line)
    return result

def load_global_commands():
    commands = {}
    eps = entry_points()
    group = eps.select(group='paste.global_paster_command')
    for p in group:
        commands[p.name] = p
    return commands

def _safe_name(dist_name):
    """Convert a distribution name to a filename-safe name."""
    return re.sub('[^a-zA-Z0-9.]', '_', dist_name).lower()

def _to_filename(name):
    """Convert a name to a filename-safe format."""
    return name.replace('-', '_').replace(' ', '_')

def egg_name(dist_name):
    return _to_filename(_safe_name(dist_name))

def egg_info_dir(base_dir, dist_name):
    all = []
    for dir_extension in ['.'] + os.listdir(base_dir):
        full = os.path.join(base_dir, dir_extension,
                            egg_name(dist_name)+'.egg-info')
        all.append(full)
        if os.path.exists(full):
            return full
    raise IOError("No egg-info directory found (looked in %s)"
                  % ', '.join(all))
