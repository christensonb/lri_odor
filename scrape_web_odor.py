""" This will create an html and csv report of LRI Odor by scraping the database from the website:
        http://www.odour.org.uk
"""
from seaborn.rest.errors import NotFoundException
from seaborn.rest.intellisense import *
from seaborn.table import SeabornTable
import time

__author__ = "Ben Christenson"
__date__ = "2016-09-03"

PROXIES = None  # {'http': 'http:///127.0.0.1:8080', 'https': 'https://127.0.0.1:8081'}
DEBUG = False


def main():
    start_time = time.time()
    conn = Connection(base_uri='http://www.odour.org.uk', proxies=PROXIES)
    odor_words = conn.keywords.get() if not DEBUG else ['almond', 'burnt']
    lri_columns = conn.columns.get()

    table = SeabornTable(columns=['ID', 'Compound', 'Class', 'CAS', 'Mass'] +
                                 lri_columns + ['Odour'] + odor_words + ['ID <Link>'],
                         key_on='ID')

    for id in range(1000, 3280) if DEBUG else xrange(1, 100000):
        if id % 100 == 0 or id == 1:
            print "Getting compound: %s" % id
        try:
            compound = conn.compound.get(id)
            assert compound['Compound']
            table.append(compound)
        except NotFoundException as e:
            if id > 5058:  # I know where are this many ids
                break

    for page in xrange(1, 2 if DEBUG else 2000):
        print 'Getting LRI for page: %s of compound: %s' % (page, len(table))
        compounds = conn.lri.get(page=page)
        for compound in compounds:
            table[compound['ID'],].update(compound)
            table[compound['ID'],][compound['Column']] = compound['LRI']
        if not compounds:
            break

    for odour in odor_words:
        print 'Getting compounds for odour: %s - %s' % (odor_words.index(odour), odour)
        ids = conn.odour.get(odour=odour)
        table.set_column(odour, '')
        for id in ids:
            if table[id,]['Odour']:
                table[id,]['Odour'] += '  "%s"' % odour
            else:
                table[id,]['Odour'] = '"%s"' % odour
            table[id,][odour] = 1

    table.sort_by_key()
    open('LRI_ODOR.html', 'w').write(table.obj_to_html())
    open('LRI_ODOR.csv', 'w').write(table.obj_to_csv())
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
        options_text = ret.split('      <OPTION VALUE=any>Any<option', 1)[1].split('</SELECT>')[0]
        columns = [word.split('>')[0] for word in options_text.split('option value=')[1:]]
        return sorted(columns)


class Compound(Endpoint):
    def get(self, compound_id):
        response = self.connection.get('cgi-bin/compound.cgi',
                                       Compound_ID=compound_id)
        text = response.split('>Odour Data Home</a><p><font size=+2><b>', 1)[1]
        compound = dict(ID=compound_id,
                        Compound=text.split('</b>')[0],
                        Class=text.split('Class:</b>', 1)[1].split('<br>')[0].strip(),
                        CAS=text.split('CAS:</b>', 1)[1].split('<br>')[0].strip(),
                        Mass=text.split('Mass:</b>', 1)[1].split('<br>')[0].strip())
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
