""" This will create an html and csv report of LRI Odor by scraping the database from the website:
        http://www.odour.org.uk
"""
from seaborn.rest.errors import NotFoundException
from seaborn.rest.intellisense import *
from seaborn.table import SeabornTable
import time
import os

__author__ = "Ben Christenson"
__date__ = "2016-09-03"

PROXIES = None  # {'http': 'http:///127.0.0.1:8080', 'https': 'https://127.0.0.1:8081'}
DEBUG = False
CSV_FILE = 'LRI_ODOR.csv'


def main():
    start_time = time.time()
    conn = Connection(base_uri='http://www.odour.org.uk', proxies=PROXIES)
    odor_words = conn.keywords.get() if not DEBUG else ['burnt']
    lri_columns = conn.columns.get()+['Unknown']
    table = SeabornTable.csv_to_obj(CSV_FILE,
                                    columns=['ID', 'Compound', 'Class', 'CAS', 'Mass'] +
                                            lri_columns + ['Odour'] + odor_words + ['ID <Link>'],
                                    key_on='ID')

    for id in (xrange(1, 100000) \
                       if not DEBUG else [2942, 3068, 3879, 3723]):
        if (id,) in table and table[(id,)]['Compound'] != '':
            continue
        if id % 100 == 0 or id == 1:
            print "Getting compound: %s" % id
        if id % 1000 == 0:
            open(CSV_FILE, 'w').write(table.obj_to_csv())
        try:
            compound = conn.compound.get(id)
            if not compound.get('Compound', None):
                raise NotFoundException("Missing Name")
            table.append(compound)
        except NotFoundException as e:
            if id > 5058:  # I know where are this many ids
                break
    open(CSV_FILE, 'w').write(table.obj_to_csv())

    for page in [5] if DEBUG else xrange(2000):
        print 'Getting LRI for page: %s of compound: %s' % (page, len(table))
        compounds = conn.lri.get(page=page)
        for compound in compounds:
            for k, v in compound.items():
                if not v:
                    compound.pop(k)
            table[compound['ID'],].update(compound)
            if not compound.get('Column') in lri_columns:
                compound['Column'] = 'Unknown'

            table[compound['ID'],][compound['Column']] = compound['LRI']
        if not compounds:
            break

    open(CSV_FILE, 'w').write(table.obj_to_csv())

    for odour in odor_words:
        print 'Getting compounds for odour: %s - %s' % (odor_words.index(odour), odour)
        ids = conn.odour.get(odour=odour)
        table.set_column(odour, '')
        for id in ids:
            if not (id,) in table:
                continue

            if table[id,]['Odour']:
                table[id,]['Odour'] += '  "%s"' % odour
            else:
                table[id,]['Odour'] = '"%s"' % odour
            table[id,][odour] = 1

    table.sort_by_key()
    open(CSV_FILE, 'w').write(table.obj_to_csv())
    open(CSV_FILE.split('.')[0] + '.html', 'w').write(table.obj_to_html())
    print "\n\nThat's All Folks in %s seconds" % round(time.time() - start_time, 2)


class Lri(Endpoint):
    def get(self, compound='', mass='', column='', lri=5000, lri_error=5000, page=1):
        """
        :param compound:
        :param mass:
        :param column:
        :param lri:
        :param lri_error:
        :param page:
        :return: list of dictionaries
        """
        ret = self.connection.get('cgi-bin/search.cgi',
                                  compound=compound,
                                  mass=mass,
                                  column=column,
                                  lri=lri,
                                  lri_error=lri_error,
                                  page=page)
        compounds_text = [compound.split('</td>') for compound in
                          ret.split("<td><a href='/cgi-bin/view.cgi?Compound_ID=")[1:]]
        compounds = [{'ID': eval(c[0].split("'")[0].strip()),
                      'Compound': c[1].split('>')[-1].strip(),
                      'Mass': eval(c[2].split('>')[-1].strip()),
                      'Column': c[3].split('>')[-1].strip(),
                      'LRI': eval(c[4].split('>')[-1].strip()),
                      'ID <Link>': '%scgi-bin/view.cgi?Compound_ID=%s' % (self.connection.base_uri,
                                                                          c[0].split("'")[0])} for c in compounds_text]
        return compounds


class Keywords(Endpoint):
    def get(self):
        """
        :return: list of str of odor keywords
        """
        ret = self.connection.get('cgi-bin/keywords.cgi')
        words = ret.split('cgi-bin/odour.cgi?odour=')
        return [word.split("'")[0] for word in words[1:]]


class Columns(Endpoint):
    def get(self):
        """
        :return: list of str of lri columns
        """
        ret = self.connection.get('lriindex.html')
        options_text = ret.split('      <OPTION VALUE=any>Any<option', 1)[1].split('</SELECT>')[0].replace('\n', ' ')
        columns = [word.split('>')[0] for word in options_text.split('option value=')[1:]]
        return sorted(columns)


class Compound(Endpoint):
    def get(self, compound_id):
        response = self.connection.get('cgi-bin/compound.cgi',
                                       Compound_ID=compound_id)
        text = response.split('>Odour Data Home</a><p><font size=+2><b>', 1)[1]
        compound = {'ID': compound_id,
                    'Compound': text.split('</b>')[0].strip(),
                    'Class': text.split('Class:</b>', 1)[1].split('<br>')[0].strip(),
                    'CAS': text.split('CAS:</b>', 1)[1].split('<br>')[0].strip(),
                    'Mass': text.split('Mass:</b>', 1)[1].split('<br>')[0].strip(),
                    'ID <Link>': '%scgi-bin/view.cgi?Compound_ID=%s'%(self.connection.base_uri,compound_id)}
        return compound


class Odour(Endpoint):
    def get(self, odour):
        """
        :param odour: str of the odor keyword
        :return: list of int of compound ids
        """
        ret = self.connection.get('cgi-bin/odour.cgi',
                                  odour=odour)
        return [eval(id.split("'")[0].strip()) for id in ret.split('cgi-bin/view.cgi?Compound_ID=')[1:]]


class Connection(ConnectionEndpoint):
    keywords = Keywords()
    columns = Columns()
    lri = Lri()
    odour = Odour()
    compound = Compound()


if __name__ == '__main__':
    main()
