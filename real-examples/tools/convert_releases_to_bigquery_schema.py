import glob
import json
import optparse
from pprint import pprint

'''
Given a set of OCDS releases, fix problems that will stop them loading
into BigQuery.
Currently this file does the following:
- Converts ID fields that are integers to string values
- Removes various additional fields found in publisher files
- Prints converted data to a newline-delimited JSON output file.
'''


def ids_to_string(mydict):
    '''
    Given a dictionary, look for any integer ID properties,
    and convert them to strings. This is because IDs in the
    OCDS definition can be either integers or strings, but
    BigQuery can't cope with mixed types.
    '''
    for k, v in mydict.items():
        if k == 'id' and type(v) is int or type(v) is float:
            mydict[k] = str(v)
        elif type(v) is dict:
            mydict[k] = ids_to_string(mydict[k])
        elif type(v) is list:
            for i, item in enumerate(v):
                if type(v[i]) is dict:
                    v[i] = ids_to_string(v[i])
    return mydict


def fix_uk_issues(data):
    '''
    Fix minor mis-naming issue, plus missing and null tags.
    '''
    if 'parties' in data:
        for p in data['parties']:
            if 'contactPoint' in p:
                if 'uri' in p['contactPoint']:
                    p['contactPoint']['url'] = p['contactPoint']['uri']
                    del p['contactPoint']['uri']
        if 'tag' not in data:
            data['tag'] = []
        if len(data['tag']) == 1 and not data['tag'][0]:
            data['tag'] = []
    return data


def fix_mexico_grupo_issues(data):
    if 'tender' in data:
        if 'metodoDeAdquisicion' in data['tender']:
            del data['tender']['metodoDeAdquisicion']
    return data


def fix_mexico_cdmx_issues(data):
    '''
    Removes extra fields.
    '''
    for k, v in data.items():
        forbidden = [
            'dateexchangeRate', 'amountyear', 'multiYear',
            'valueyear', 'exchangeRate']
        if k in forbidden:
            del data[k]
        elif type(v) is dict:
            data[k] = fix_mexico_cdmx_issues(data[k])
        elif type(v) is list:
            for i, item in enumerate(v):
                if type(v[i]) is dict:
                    v[i] = fix_mexico_cdmx_issues(v[i])
    return data


def fix_moldova_issues(data):
    '''
    Fix typo'd field name.
    '''
    if 'tender' in data:
        if 'numberOfTenders' in data['tender']:
            data['tender']['numberOfTenderers'] = \
                data['tender']['numberOfTenders']
            del data['tender']['numberOfTenders']
    return data


def fix_nsw_issues(data):
    '''
    Fix typo'd field name.
    '''
    permitted_tender_keys = [
        u'procurementMethod', u'amendment',
        u'awardPeriod', u'mainProcurementCategory', u'enquiryPeriod',
        u'minValue', u'numberOfTenderers', u'value', u'tenderers',
        u'id', u'description', u'amendments', u'documents', u'title',
        u'awardCriteria', u'procurementMethodRationale', u'contractPeriod',
        u'status', u'eligibilityCriteria', u'tenderPeriod',
        u'procurementMethodDetails', u'additionalProcurementCategories',
        u'submissionMethod', u'milestones', u'submissionMethodDetails',
        u'items', u'awardCriteriaDetails', u'hasEnquiries', u'procuringEntity'
    ]
    forbidden_keys = []
    if 'tender' in data:
        for k in data['tender']:
            if unicode(k) not in permitted_tender_keys:
                forbidden_keys.append(k)
    for f in forbidden_keys:
        del data['tender'][f]
        # if 'multiAgencyAccess' in data['tender']:
        #     del data['tender']['multiAgencyAccess']
        # if 'PPstatus' in data['tender']:
        #     del data['tender']['PPstatus']
        # if 'estimatedDateToMarket' in data['tender']:
        #     del data['tender']['estimatedDateToMarket']
        # if 'inheritanceType' in data['tender']:
        #     del data['tender']['inheritanceType']
        # if 'tenderType' in data['tender']:
        #     del data['tender']['tenderType']
        # if 'RFTUUID' in data['tender']:
        #     del data['tender']['RFTUUID']
        if 'amendment' in data['tender'] and \
                'changes' in data['tender']['amendment']:
            for c in data['tender']['amendment']['changes']:
                if 'former_value' in c \
                        and type(c['former_value']) is not str:
                    c['former_value'] = str(c['former_value'])
    if 'awards' in data:
        for a in data['awards']:
            if 'CNUUID' in a:
                del a['CNUUID']
            if 'valueDescription' in a:
                del a['valueDescription']
            if 'title' in a and \
                    (type(a['title']) is int or type(a['title']) is float):
                a['title'] = str(a['title'])
            # if 'id' in a and \
            #         (type(a['id']) is int or type(a['id']) is float):
            #     a['id'] = str(a['id'])

    return data


def fix_taiwan_issues(data):
    '''
    Fix typo'd field name.
    '''
    if 'name' in data:
        del data['name']
    name = data['packageInfo']['publisher']
    data['packageInfo']['publisher'] = {
        'name': name
    }
    data['packageInfo']['publishedDate'] = \
        data['packageInfo']['publishedDate'] + ' 00:00'
    # TODO: Convert tag from string to array.
    # Also, check how it passed validation?
    return data


def main():
    usage = 'Usage: %prog [ --all --cont ]'
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-f', '--filepath', action='store', default=None,
                      help='Path to files, e.g. parguay/sample')
    (options, args) = parser.parse_args()
    if not options.filepath:
        parser.error('You must supply a filepath, using the -f argument')

    all_data = []
    files = glob.glob('%s*' % options.filepath)
    for i, filename in enumerate(files):
        # print filename
        if not i % 1000:
            print 'Processing file %s of %s' % (i, len(files))
        if not filename.endswith('.json'):
            print('Skipping non-JSON file %s' % filename)
            continue
        with open(filename, 'r') as file:
            try:
                data = json.load(file)
            except Exception as e:
                print('Problem loading', filename)
                print(e)
                continue
            data = ids_to_string(data)
            data = fix_uk_issues(data)
            data = fix_mexico_grupo_issues(data)
            data = fix_mexico_cdmx_issues(data)
            data = fix_moldova_issues(data)
            data = fix_nsw_issues(data)
            data = fix_taiwan_issues(data)
        all_data.append(data)
    with open('all-releases.json', 'w') as writefile:
        for d in all_data:
            json.dump(d, writefile)
            writefile.write('\n')

if __name__ == '__main__':
    main()
