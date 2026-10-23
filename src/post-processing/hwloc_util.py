#!/usr/bin/env python3

"""
# MIT License
#
# Copyright (c) 2023-2025 University of Oregon, Kevin Huck
# Copyright (c) 2026 Advanced Micro Devices, Inc. All rights reserved.
# SPDX-License-Identifier: MIT
# See LICENSE in the project root for license information.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""

import json
import pandas as pd
import glob
import os
import re
import sys
pd.options.mode.chained_assignment = None  # default='warn'
template_location = "@CMAKE_INSTALL_PREFIX@/etc/"
d3_js = template_location + "d3.v7.js"
template = template_location + "zs-hwloc-template.html"
standalone_template = template_location + "zs-hwloc-template-standalone.html"

def parseArgs():
    import argparse
    parser = argparse.ArgumentParser(description='Post-process ZeroSum HWLOC topology utilization.')
    parser.add_argument('--standalone', dest='standalone', action='store_true',
        help='Generate standalone HTML file to be used offline (default: false)', default=False)
    args = parser.parse_args()
    return args

def parseData():
    # Read the CSV data - use dtype to speed it up
    dtype={"hostname": str, "rank": int, "shmrank": int, "step": int, "resource": str, "type": str, "index": int, "name": str, "value": str}
    all_files = glob.glob(os.path.join('.', "zs.data.*.csv"))
    df = pd.concat((pd.read_csv(f,dtype=dtype) for f in all_files), ignore_index=True)
    return df

def parseHWTData(df):
    print("HWT Data...")
    # select the hardware threads
    hwt = df.loc[df['resource'] == 'HWT']
    # Convert the value to a number
    hwt['value'] = pd.to_numeric(hwt['value'])
    # drop the step column
    #hwt = hwt.drop('step', axis=1)
    # select only user time
    hwt_user = hwt[hwt.name == 'user']
    # Group by everything except value to get the mean value
    mean_cols = ['value','step']
    hwt_mean = hwt_user.groupby([c for c in hwt_user.columns if c not in mean_cols]).mean()
    # Reset indices
    hwt_mean.reset_index(inplace=True)
    # drop the name column
    hwt_mean.drop('name', axis=1, inplace=True)
    # Group by everything except name to get the mean value
    sum_cols = ['value','step']
    hwt_sum = hwt_mean.groupby([c for c in hwt_mean.columns if c not in sum_cols]).sum()
    # Reset indices
    hwt_sum.reset_index(inplace=True)
    return hwt_sum,hwt

def parseGPUData(df):
    print("GPU Data...")
    # First, get JUST the GPU data.
    gpu_only = df.loc[df['resource'] == 'GPU']
    # Split the data into properties and metrics.
    gpu_metrics,gpu_properties = [y for x, y in gpu_only.groupby('type')]
    # Find this:
    # "x1921c0s0b0n0",1,0,0,"GPU","Property","0","PCI Address","0000:18:00.0"
    # select the GPUs
    gpu = gpu_properties.loc[(gpu_properties['resource'] == 'GPU') & (gpu_properties['name'] == 'PCI Address')]
    if gpu.empty:
        gpu = gpu_properties.loc[(gpu_properties['resource'] == 'GPU') & (gpu_properties['name'] == 'Bus ID')]
    addresses = {}
    for index, row in gpu.iterrows():
        # our key is a tuple of three values, hostname, the MPI rank and the GPU index
        addresses[(row['hostname'],row['rank'],row['index'])] = row['value'].lower()
    # Get the utilization data for each gpu
    gpu = gpu_metrics.loc[(gpu_metrics['name'].str.contains('L0 All Engines, subdevice'))]
    print("")
    tiles = True
    scale = 100.0
    if gpu.empty:
        gpu = gpu_metrics.loc[(gpu_metrics['name'] == 'Utilization %')]
        tiles = False
        scale = 1.0
    if gpu.empty:
        gpu = gpu_metrics.loc[(gpu_metrics['name'] == 'Device Busy %')]
        tiles = False
        scale = 1.0

    # Convert the value to a number
    gpu['value'] = pd.to_numeric(gpu['value']) * scale
    # Group by everything except value to get the mean value
    mean_cols = ['value','step']
    gpu_mean = gpu.groupby([c for c in gpu.columns if c not in mean_cols]).mean()
    # Reset indices
    gpu_mean.reset_index(inplace=True)
    for index, row in gpu_mean.sort_values(by=['hostname','rank','name']).iterrows():
        subdevice = '0'
        if tiles:
            p = re.compile(r'L0 All Engines, subdevice (\d+), Active Time')
            subdevice = p.findall(row['name'])[0]
        gpu_properties2 = gpu_properties.loc[(gpu_properties['rank'] == row['rank']) & (gpu_properties['index'] == row['index'])]
        gpu_properties3 = gpu_properties2.loc[(gpu_properties2['hostname'].str.fullmatch(row['hostname']))]
        properties = {}
        for index2, row2 in gpu_properties3.sort_values(by=['name']).iterrows():
            properties[row2['name']] = row2['value']
        addresses[(row['hostname'],row['rank'],row['index'])] = list((addresses[(row['hostname'],row['rank'],row['index'])], row['value'], subdevice, properties))
    return addresses

def traverseHWTTree(tree, in_hostname, df, hwt_all, spinner):
    utilization = int(tree['utilization'])
    rank = int(tree['rank'])
    sys.stdout.write(next(spinner))
    sys.stdout.flush()
    sys.stdout.write('\b')
    if tree['name'] == "Machine":
        # extract the hostname from the detail_name
        details = tree['detail_name'].split(',')
        in_hostname = details[0]

    # Is this a processing unit (HWT)? if so, assign utilization
    if tree['name'].startswith("PU L#"):
        name = tree['name']
        tokens = name.split()
        osindex = tokens[2]
        osindex = int(osindex[2:])
        if osindex in df['index'].values:
            # Multiple ranks may report this HWT index. Attribute the PU to the
            # rank with highest observed user-time for stable ownership mapping.
            matches = df.loc[(df['index'] == osindex) & (df['hostname'] == in_hostname)]
            if not matches.empty:
                top = matches.loc[matches['value'].idxmax()]
                utilization = top['value']
                rank = int(top['rank'])
            """ # Disabled for now - enable when we have time-slider in the hTML template
            # Get all metrics
            metrics = hwt_all['name'].unique().tolist()
            partial_values = hwt_all.loc[(hwt_all['index'] == osindex) & (df['hostname'] == in_hostname)]
            for m in metrics:
                values = partial_values.loc[(partial_values['name'] == m), 'value'].to_numpy().tolist()
                tree[m] = values
            """
    else:
        # otherwise, aggregate the children
        if 'children' in tree.keys():
            newChildren = []
            for c in tree['children']:
                newChild = traverseHWTTree(c, in_hostname, df, hwt_all, spinner)
                if tree['name'].startswith("Core L#"):
                    utilization += newChild['utilization']
                    rank = max(rank,newChild['rank'])
                newChildren.append(newChild)
            tree['children'] = newChildren
            utilization = utilization / len(tree['children'])
    tree['utilization'] = utilization;
    tree['detail_name'] = tree['detail_name'].lstrip(', ');
    tree['rank'] = rank;
    return tree

def spinning_cursor():
    while True:
        for cursor in '|/-\\':
            yield cursor

def traverseGPUTree(tree, in_hostname, in_rank, in_index, address, in_utilization, subdevice, properties):
    utilization = int(tree['utilization'])
    rank = int(tree['rank'])
    duplicate = False
    if tree['name'] == "Machine":
        # is this the right machine?
        if not tree['detail_name'].startswith(in_hostname):
            # If not, don't change anything and don't recurse
            return tree,duplicate
    if tree['name'].startswith("PCIDev"):
        detail_name = tree['detail_name']
        if address in detail_name:
            # If we have already assigned this one, we need a duplicate
            if 'subdevice' in tree and tree['subdevice'] != subdevice:
                duplicate = True
                detail_name = detail_name[:detail_name.find('subdevice:')]
                tree['detail_name'] = detail_name + 'subdevice: ' + subdevice
            else:
                for key,value in properties.items():
                    tree['detail_name'] += ', ' + key + ': ' + value
                tree['detail_name'] += ', subdevice: ' + subdevice
            tree['subdevice'] = subdevice
            utilization = in_utilization
            rank = in_rank
    else:
        if 'children' in tree.keys():
            newChildren = []
            for c in tree['children']:
                # The child is mutable, so make a copy first
                oldChild = c.copy()
                newChild,duplicate = traverseGPUTree(c, in_hostname, in_rank, in_index, address, in_utilization, subdevice, properties)
                if duplicate:
                    # Keek the old child
                    newChildren.append(oldChild)
                    duplicate = False
                newChildren.append(newChild)
            tree['children'] = newChildren
    tree['utilization'] = utilization;
    tree['rank'] = rank;
    return tree,duplicate

def simplifyTree(tree):
    if 'children' in tree.keys():
        for c in tree['children']:
            simplifyTree(c)
    if tree['name'].startswith("PU L#"):
        tree['name'] = "PU"
    if tree['name'].startswith("Core L#"):
        tree['name'] = "Core"
    return tree

def _extract_logical_index(name, detail_name):
    m = re.search(r'L#(\d+)', name or '')
    if m:
        return int(m.group(1))
    m = re.search(r'Logical index:\s*(\d+)', detail_name or '')
    if m:
        return int(m.group(1))
    return 1 << 30

def _extract_bus_id(detail_name):
    m = re.search(r'bus id:\s*([0-9a-fA-F]{4}):([0-9a-fA-F]{2}):([0-9a-fA-F]{2})\.([0-7])', detail_name or '')
    if m:
        domain = int(m.group(1), 16)
        bus = int(m.group(2), 16)
        dev = int(m.group(3), 16)
        fn = int(m.group(4), 16)
        return (domain << 16) + (bus << 8) + (dev << 3) + fn
    return 1 << 30

def _min_pu_logical_index(node):
    name = node.get('name', '')
    detail = node.get('detail_name', '')
    if name.startswith("PU L#"):
        return _extract_logical_index(name, detail)
    if 'children' not in node.keys() or len(node['children']) == 0:
        return 1 << 30
    return min(_min_pu_logical_index(c) for c in node['children'])

def _node_sort_key(node):
    name = node.get('name', '')
    detail = node.get('detail_name', '')
    logical = _extract_logical_index(name, detail)
    bus = _extract_bus_id(detail)
    min_pu = _min_pu_logical_index(node)

    # Keep compute hierarchy in logical PU order; sort PCI topology by BDF.
    if name.startswith("Bridge") or name.startswith("PCIDev"):
        return (1, bus, logical, name)
    return (0, min_pu, logical, bus, name)

def _node_sort_index(node, fallback=0):
    name = node.get('name', '')
    detail = node.get('detail_name', '')
    logical = _extract_logical_index(name, detail)
    if logical < (1 << 30):
        return logical
    bus = _extract_bus_id(detail)
    if bus < (1 << 30):
        return bus
    min_pu = _min_pu_logical_index(node)
    if min_pu < (1 << 30):
        return min_pu
    return fallback

def sortTreeChildren(tree):
    if 'children' in tree.keys():
        for c in tree['children']:
            sortTreeChildren(c)
        tree['children'] = sorted(tree['children'], key=_node_sort_key)
    return tree

def annotateRenderOrder(tree, fallback=0):
    tree['sort_index'] = tree.get('sort_index', _node_sort_index(tree, fallback))
    if 'children' not in tree.keys():
        return tree

    for idx, child in enumerate(tree['children']):
        # Preserve sibling order explicitly for D3 partition rendering.
        child['render_order'] = idx
        # Provide a sortable index at all levels; fall back to sibling order.
        child['sort_index'] = _node_sort_index(child, idx)
        annotateRenderOrder(child, idx)

    return tree

def updateTree(hwt_df, hwt_all, gpu_addresses):
    all_files = glob.glob(os.path.join('.', "zs.topology.*.json"))
    job = {}
    job['name'] = 'job'
    job['detail_name'] = '(jobid)'
    job['utilization'] = 0
    job['rank'] = -1;
    job['children'] = []
    for f in all_files:
        fp = open(f, 'r')
        tree = json.load(fp)
        job['children'].append(tree)
        fp.close()
    spinner = spinning_cursor()
    in_hostname = ''
    tree = traverseHWTTree(job, in_hostname, hwt_df, hwt_all, spinner)
    for key,value in gpu_addresses.items():
        tree,modified = traverseGPUTree(tree, key[0], key[1], key[2], value[0], value[1], value[2], value[3])
    tree = sortTreeChildren(tree)
    tree = annotateRenderOrder(tree)
    tree = simplifyTree(tree)
    return tree

def main():
    args = parseArgs()
    print("Parsing CSV data...")
    df = parseData()
    print("Extracting CSV data...")
    hwt_df,hwt_all = parseHWTData(df)
    gpu_addresses = parseGPUData(df)
    print("Updating JSON tree (may take some time)...")
    tree = updateTree(hwt_df, hwt_all, gpu_addresses)
    print("Writing HTML...")
    outfile="zs-topology.html"
    if args.standalone:
        with open(standalone_template,'r') as file:
            populate_me = file.read()
        with open(d3_js,'r') as file:
            javascript = file.read()
        java_as_string = json.dumps(tree)
        from string import Template
        s = Template(populate_me)
        with open(outfile, 'w') as fp:
            fp.write(s.substitute(JSONDATA=java_as_string, SCRIPT_TEXT=javascript))

    else:
        with open(template,'r') as file:
            populate_me = file.read()
        with open(d3_js,'r') as file:
            javascript = file.read()
        java_as_string = json.dumps(tree)
        from string import Template
        s = Template(populate_me)
        with open(outfile, 'w') as fp:
            fp.write(s.substitute(JSONDATA=java_as_string))
    os.chmod(outfile, 0o666)

if __name__ == '__main__':
    main()

