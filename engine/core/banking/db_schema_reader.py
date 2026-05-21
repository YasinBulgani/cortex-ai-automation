"""
TestwrightAI Banking — Database Schema Reader
Reads table/column/FK structure from SQLite, PostgreSQL, MySQL.
Maps column names → test data generator hints.
"""
import re
import sqlite3
from typing import Dict, List, Any, Optional


# ── Column-name → generator heuristic (regex → generator_key) ─────────────
COLUMN_HINTS = [
    # Turkish identity — broad patterns first
    (r'tc[_\s]?kimlik[_\s]?no|tc[_\s]?no$|^tc$|kimlik[_\s]?no', 'tc_kimlik'),
    (r'vkn|vergi[_\s]?kimlik',                         'vkn'),
    # Financial identifiers
    (r'iban',                                          'iban'),
    (r'kart[_\s]?(no|numarasi)|card[_\s]?no',        'card_number'),
    (r'^cvv$|^cvc$|^cvv2$',                           'cvv'),
    (r'son[_\s]?kullanma|gecerlilik|expiry',          'card_expiry'),
    # Personal
    (r'^adi?$|^isim$|first[_\s]?name',               'first_name'),
    (r'^soyadi?$|last[_\s]?name|surname',             'last_name'),
    (r'dogum[_\s]?(tarihi|yili)?|birth',              'birth_date'),
    (r'^cinsiyet$|^gender$',                           'gender'),
    (r'telefon|phone|gsm|cep',                         'phone'),
    (r'e[_\s]?mail|eposta',                            'email'),
    (r'adres|address',                                 'address'),
    (r'sehir|city|^il$',                               'city'),
    # Financial
    (r'bakiye|balance',                                'balance'),
    (r'(kullanilan|mevcut)[_\s]?limit',               'used_limit'),
    (r'tutar|amount|miktar',                           'amount'),
    (r'(kart|kredi)[_\s]?limit',                      'credit_limit'),
    (r'limit',                                         'credit_limit'),
    (r'faiz|interest|oran',                            'interest_rate'),
    (r'ciro|gelir|maas|income|revenue',                'income'),
    (r'borc|debt|kalan[_\s]?borc',                    'debt_amount'),
    (r'(aylik|monthly)[_\s]?taksit',                  'installment'),
    (r'vade[_\s]?(ay|adet|sayisi)?|term_months',      'term_months'),
    (r'odenen[_\s]?taksit',                            'small_int'),
    # References
    (r'referans|ref[_\s]?no|reference',                'reference_no'),
    (r'swift',                                         'swift_code'),
    # Date/Time
    (r'(kayit|acilis|baslangic)[_\s]?tarihi',         'past_date'),
    (r'(kapanis|bitis)[_\s]?tarihi',                  'future_date'),
    (r'islem[_\s]?tarihi',                             'transaction_date'),
    (r'tarih|date|created_at|updated_at',              'date'),
    # Flags / Enums
    (r'^durum$|^status$',                              'status'),
    (r'^aktif$|^active$|is_active',                    'bool_flag'),
    (r'temerrut|default[_\s]?flag',                   'temerrut_flag'),
    (r'segment',                                       'segment'),
    (r'(hesap|kredi|islem|kart)[_\s]?turu?$',        'type_enum'),
    (r'^tur[ue]?$|^type$|^cesit$',                    'type_enum'),
    (r'para[_\s]?birimi|currency',                    'currency'),
    # Corporate
    (r'sirket|company|firma',                          'company_name'),
    (r'risk[_\s]?skoru?|credit[_\s]?score',            'risk_score'),
    (r'sektor|sector|industry',                        'sector'),
    (r'vergi[_\s]?(dairesi|office)',                  'tax_office'),
    (r'calisan|employee_count',                        'employee_count'),
    (r'(veren|ihrac)[_\s]?(banka|bank)',              'bank_name'),
    (r'aciklama|description|explanation|^not[_\s]',   'description'),
    (r'^banka[_\s]?kodu?$|^bank[_\s]?code$',         'bank_code'),
    (r'ulke|country',                                  'country'),
    # Kaynak/hedef
    (r'(gonderici|alici|kaynak|hedef)[_\s]?iban',    'iban'),
    (r'(kaynak|hedef)[_\s]?para',                     'currency'),
    (r'(kaynak|hedef)[_\s]?tutar',                    'amount'),
    (r'^kur$|doviz[_\s]?kur',                         'exchange_rate'),
    (r'ana[_\s]?para|principal',                       'amount'),
]

SQL_TYPE_FALLBACK = {
    'INTEGER': 'int', 'INT': 'int', 'BIGINT': 'int', 'SMALLINT': 'small_int',
    'TINYINT': 'bool_flag', 'BOOLEAN': 'bool_flag', 'BOOL': 'bool_flag',
    'DECIMAL': 'amount', 'NUMERIC': 'amount', 'REAL': 'amount',
    'FLOAT': 'amount', 'DOUBLE': 'amount',
    'TEXT': 'text', 'VARCHAR': 'text', 'CHAR': 'text', 'NVARCHAR': 'text',
    'DATE': 'date', 'DATETIME': 'transaction_date', 'TIMESTAMP': 'transaction_date',
    'BLOB': 'text',
}


def infer_generator(col_name: str, col_type: str) -> str:
    """Best-effort generator selection based on column name + SQL type."""
    name = col_name.lower().strip()
    for pattern, gen in COLUMN_HINTS:
        if re.search(pattern, name):
            return gen
    type_key = col_type.upper().split('(')[0].strip()
    return SQL_TYPE_FALLBACK.get(type_key, 'text')


class ColumnDef:
    def __init__(self, cid, name, col_type, notnull, dflt_value, pk):
        self.cid        = cid
        self.name       = name
        self.col_type   = col_type or 'TEXT'
        self.notnull    = bool(notnull)
        self.default    = dflt_value
        self.is_pk      = bool(pk)
        self.is_fk      = False
        self.fk_table   = None
        self.fk_column  = None
        self.generator  = infer_generator(name, col_type or '')
        self.nullable   = not bool(notnull) and not bool(pk)

    def to_dict(self):
        return {
            'name':       self.name,
            'type':       self.col_type,
            'notnull':    self.notnull,
            'is_pk':      self.is_pk,
            'is_fk':      self.is_fk,
            'fk_table':   self.fk_table,
            'fk_column':  self.fk_column,
            'generator':  self.generator,
            'nullable':   self.nullable,
        }


class TableDef:
    def __init__(self, name: str, columns: List[ColumnDef]):
        self.name      = name
        self.columns   = columns
        self.parents: set = set()
        self.row_count = 0

    def ddl_snippet(self) -> str:
        lines = [f"TABLE {self.name}:"]
        for c in self.columns:
            flags = []
            if c.is_pk: flags.append("PK")
            if c.is_fk: flags.append(f"FK→{c.fk_table}.{c.fk_column}")
            if c.notnull: flags.append("NOT NULL")
            flag_str = " [" + ", ".join(flags) + "]" if flags else ""
            lines.append(f"  {c.name} {c.col_type}{flag_str}  -- generator: {c.generator}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            'name':       self.name,
            'columns':    [c.to_dict() for c in self.columns],
            'pk_columns': [c.name for c in self.columns if c.is_pk],
            'fk_columns': [
                {'column': c.name, 'ref_table': c.fk_table, 'ref_column': c.fk_column}
                for c in self.columns if c.is_fk
            ],
            'parents':    list(self.parents),
            'row_count':  self.row_count,
            'ddl':        self.ddl_snippet(),
        }


class SchemaReader:
    """Read table/column/FK structure from a database."""

    def __init__(self, db_type: str = 'sqlite', conn_str: str = ''):
        self.db_type  = db_type
        self.conn_str = conn_str
        self._conn    = None

    # ── Connection ─────────────────────────────────────────────────────────

    def connect(self):
        if self.db_type == 'sqlite':
            self._conn = sqlite3.connect(self.conn_str)
            self._conn.row_factory = sqlite3.Row
        elif self.db_type == 'postgresql':
            import psycopg2
            self._conn = psycopg2.connect(self.conn_str)
        elif self.db_type == 'mysql':
            import pymysql
            self._conn = pymysql.connect(**_parse_mysql_url(self.conn_str))
        else:
            raise ValueError(f"Desteklenmeyen DB tipi: {self.db_type}")

    def disconnect(self):
        if self._conn:
            try: self._conn.close()
            except: pass
            self._conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.disconnect()

    # ── Schema reading ──────────────────────────────────────────────────────

    _SUPPORTED_DB_TYPES = ("sqlite", "postgresql", "mysql")

    def read_schema(self) -> Dict[str, 'TableDef']:
        """Veritabani sema bilgisini oku.

        Desteklenen tipler: sqlite, postgresql, mysql.
        Desteklenmeyen tipler icin ValueError firlatar — callariniz bu hataya gore
        kullaniciya anlasilir bir mesaj gostermelidir.
        """
        if not self._conn:
            self.connect()
        if self.db_type == 'sqlite':
            return self._read_sqlite()
        elif self.db_type == 'postgresql':
            return self._read_postgresql()
        elif self.db_type == 'mysql':
            return self._read_mysql()
        supported = ", ".join(self._SUPPORTED_DB_TYPES)
        raise ValueError(
            f"Desteklenmeyen veritabani tipi: '{self.db_type}'. "
            f"Desteklenen tipler: {supported}"
        )

    def _read_sqlite(self) -> Dict[str, 'TableDef']:
        c = self._conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        table_names = [r[0] for r in c.fetchall()]

        tables: Dict[str, TableDef] = {}
        for tname in table_names:
            c.execute(f"PRAGMA table_info(`{tname}`)")
            cols = [ColumnDef(r[0], r[1], r[2], r[3], r[4], r[5]) for r in c.fetchall()]

            c.execute(f"PRAGMA foreign_key_list(`{tname}`)")
            for fk in c.fetchall():
                fk_from, fk_table, fk_to = fk[3], fk[2], fk[4]
                for col in cols:
                    if col.name == fk_from:
                        col.is_fk     = True
                        col.fk_table  = fk_table
                        col.fk_column = fk_to
                        col.generator = 'fk_ref'

            tdef = TableDef(tname, cols)
            tdef.parents = {col.fk_table for col in cols if col.is_fk and col.fk_table}

            try:
                c.execute(f"SELECT COUNT(*) FROM `{tname}`")
                tdef.row_count = c.fetchone()[0]
            except:
                tdef.row_count = 0

            tables[tname] = tdef
        return tables

    def _read_postgresql(self) -> Dict[str, 'TableDef']:
        """PostgreSQL schema reader (psycopg2)."""
        c = self._conn.cursor()
        c.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        table_names = [r[0] for r in c.fetchall()]
        tables: Dict[str, TableDef] = {}

        for tname in table_names:
            c.execute("""
                SELECT
                    ordinal_position - 1,
                    column_name,
                    data_type,
                    CASE WHEN is_nullable = 'NO' THEN 1 ELSE 0 END,
                    column_default,
                    CASE WHEN column_name IN (
                        SELECT kcu.column_name FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                            ON tc.constraint_name = kcu.constraint_name
                        WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_name = %s
                    ) THEN 1 ELSE 0 END
                FROM information_schema.columns
                WHERE table_name = %s AND table_schema = 'public'
                ORDER BY ordinal_position
            """, (tname, tname))
            cols = [ColumnDef(*r) for r in c.fetchall()]

            c.execute("""
                SELECT kcu.column_name, ccu.table_name, ccu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = %s
            """, (tname,))
            for fk in c.fetchall():
                fk_from, ref_table, ref_col = fk
                for col in cols:
                    if col.name == fk_from:
                        col.is_fk     = True
                        col.fk_table  = ref_table
                        col.fk_column = ref_col
                        col.generator = 'fk_ref'

            tdef = TableDef(tname, cols)
            tdef.parents = {col.fk_table for col in cols if col.is_fk and col.fk_table}
            try:
                c.execute(f'SELECT COUNT(*) FROM "{tname}"')
                tdef.row_count = c.fetchone()[0]
            except:
                tdef.row_count = 0
            tables[tname] = tdef

        return tables

    def _read_mysql(self) -> Dict[str, 'TableDef']:
        """MySQL schema reader (pymysql)."""
        c = self._conn.cursor()
        db_name = self.conn_str.split('/')[-1] if '/' in self.conn_str else ''
        c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE() ORDER BY table_name")
        table_names = [r[0] for r in c.fetchall()]
        tables: Dict[str, TableDef] = {}

        for tname in table_names:
            c.execute(f"DESCRIBE `{tname}`")
            cols = []
            for i, r in enumerate(c.fetchall()):
                # Field, Type, Null, Key, Default, Extra
                is_pk = 'PRI' in (r[3] or '')
                is_nn = r[2] == 'NO'
                cols.append(ColumnDef(i, r[0], r[1], is_nn, r[4], is_pk))

            c.execute(f"""
                SELECT column_name, referenced_table_name, referenced_column_name
                FROM information_schema.key_column_usage
                WHERE table_name = %s AND referenced_table_name IS NOT NULL
                AND table_schema = DATABASE()
            """, (tname,))
            for fk in c.fetchall():
                fk_from, ref_table, ref_col = fk
                for col in cols:
                    if col.name == fk_from:
                        col.is_fk     = True
                        col.fk_table  = ref_table
                        col.fk_column = ref_col
                        col.generator = 'fk_ref'

            tdef = TableDef(tname, cols)
            tdef.parents = {col.fk_table for col in cols if col.is_fk and col.fk_table}
            try:
                c.execute(f"SELECT COUNT(*) FROM `{tname}`")
                tdef.row_count = c.fetchone()[0]
            except:
                tdef.row_count = 0
            tables[tname] = tdef

        return tables

    # ── Helpers ─────────────────────────────────────────────────────────────

    def topological_order(self, tables: Dict[str, 'TableDef']) -> List[str]:
        visited, order = set(), []
        def visit(n):
            if n in visited or n not in tables: return
            visited.add(n)
            for p in tables[n].parents: visit(p)
            order.append(n)
        for n in tables: visit(n)
        return order

    def schema_to_dict(self, tables: Dict[str, 'TableDef']) -> dict:
        order = self.topological_order(tables)
        return {n: tables[n].to_dict() for n in order}

    def schema_to_ddl(self, tables: Dict[str, 'TableDef']) -> str:
        order = self.topological_order(tables)
        return "\n\n".join(tables[n].ddl_snippet() for n in order)


def _parse_mysql_url(url: str) -> dict:
    """Parse mysql://user:pass@host:port/db into pymysql kwargs."""
    import re
    m = re.match(r'mysql://([^:]+):([^@]+)@([^:/]+):?(\d+)?/(.+)', url)
    if not m:
        raise ValueError(f"Invalid MySQL URL: {url}")
    return dict(host=m.group(3), port=int(m.group(4) or 3306),
                user=m.group(1), password=m.group(2), db=m.group(5))
