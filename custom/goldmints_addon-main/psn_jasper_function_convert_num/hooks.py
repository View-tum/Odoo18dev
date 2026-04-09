def create_convert_num_functions(env):
    cr = env.cr

    # สร้างและเติมข้อมูลตารางสำหรับภาษาไทย
    cr.execute("""
    CREATE TABLE IF NOT EXISTS convert_num_th_num (
        Id integer PRIMARY KEY,
        Text varchar(255)
    );
    """)
    cr.execute("""
    INSERT INTO convert_num_th_num (Id, Text) VALUES
    (0, 'ศูนย์'), (1, 'หนึ่ง'), (2, 'สอง'), (3, 'สาม'), (4, 'สี่'),
    (5, 'ห้า'), (6, 'หก'), (7, 'เจ็ด'), (8, 'แปด'), (9, 'เก้า')
    ON CONFLICT (Id) DO NOTHING;
    """)

    cr.execute("""
    CREATE TABLE IF NOT EXISTS convert_num_th_rank (
        Id integer PRIMARY KEY,
        Text varchar(255)
    );
    """)
    cr.execute("""
    INSERT INTO convert_num_th_rank (Id, Text) VALUES
    (0, ''), (1, 'สิบ'), (2, 'ร้อย'), (3, 'พัน'), (4, 'หมื่น'), (5, 'แสน'),
    (6, 'ล้าน'), (7, 'สิบล้าน'), (8, 'ร้อยล้าน'), (9, 'พันล้าน')
    ON CONFLICT (Id) DO NOTHING;
    """)

    # สร้างฟังก์ชัน convert_num_th
    cr.execute("""
    CREATE OR REPLACE FUNCTION public.convert_num_th(val numeric)
    RETURNS bpchar AS $BODY$
    DECLARE
        bahtTH varchar DEFAULT '';
        numberVAl integer DEFAULT 0;
        intVal varchar(50);
        decVal varchar(50);
        i integer := 0;
        iLen integer;
    BEGIN
        intVal := split_part(cast(val as text), '.', 1);
        decVal := split_part(cast(val as text), '.', 2);

        IF(val = 0) THEN
            bahtTH := 'ศูนย์บาทถ้วน';
        ELSE
            iLen := LENGTH(intVal);
            WHILE (i < iLen) LOOP
                numberVAl := CAST(SUBSTRING(intVal, i + 1, 1) AS INTEGER);
                IF(numberVAl <> 0) THEN
                    IF((i = (LENGTH(intVal) - 1)) AND (numberVAl = 1)) THEN
                        IF(LENGTH(intVal) = 1) THEN
                            bahtTH := CONCAT(bahtTH,'หนึ่ง');
                        ELSE
                            bahtTH := CONCAT(bahtTH, 'เอ็ด');
                        END IF;
                    ELSIF((i = (LENGTH(intVal) - 2)) AND (numberVAl = 2)) THEN
                        bahtTH := CONCAT(bahtTH,'ยี่');
                    ELSIF((i = (LENGTH(intVal) - 8)) AND (numberVAl = 2)) THEN
                        bahtTH := CONCAT(bahtTH,'ยี่');
                    ELSIF((i = (LENGTH(intVal) - 2)) AND (numberVAl = 1)) THEN
                        bahtTH := CONCAT(bahtTH,'');
                    ELSIF((i = (LENGTH(intVal) - 8)) AND (numberVAl = 1)) THEN
                        bahtTH := CONCAT(bahtTH,'');
                    ELSE
                        bahtTH := CONCAT(bahtTH, (SELECT Text FROM convert_num_th_num WHERE Id = numberVAl LIMIT 1));
                    END IF;
                    bahtTH := CONCAT(bahtTH, (SELECT Text FROM convert_num_th_rank WHERE Id = ((LENGTH(intVal) - i) - 1) LIMIT 1));
                END IF;
                i := i + 1;
            END LOOP;

            bahtTH := CONCAT(bahtTH, 'บาท');
            IF(length(decVal) = 0) or (CAST(decVal as integer) = 0) THEN
                bahtTH := CONCAT(bahtTH, 'ถ้วน');
            ELSIF (SUBSTRING(decVal, 1, 1) = '0') THEN
                numberVAl := CAST(SUBSTRING(decVal, 2, 1) AS INTEGER);
                bahtTH := CONCAT(bahtTH, (SELECT Text FROM convert_num_th_num WHERE Id = numberVAl LIMIT 1));
                bahtTH := CONCAT(bahtTH, 'สตางค์');
            ELSE
                i := 0;
                iLen := LENGTH(decVal);
                WHILE (i < iLen) LOOP
                    numberVAl := CAST(SUBSTRING(decVal, i + 1, 1) AS INTEGER);
                    IF(numberVAl <> 0) THEN
                        IF((i = (LENGTH(decVal) - 1)) AND (numberVAl = 1)) THEN
                            bahtTH := CONCAT(bahtTH, 'เอ็ด');
                        ELSIF((i = (LENGTH(decVal) - 2)) AND (numberVAl = 2)) THEN
                            bahtTH := CONCAT(bahtTH, 'ยี่');
                        ELSIF((i = (LENGTH(decVal) - 2)) AND (numberVAl = 1)) THEN
                            bahtTH := CONCAT(bahtTH, '');
                        ELSE
                            bahtTH := CONCAT(bahtTH, (SELECT Text FROM convert_num_th_num WHERE Id = numberVAl LIMIT 1));
                        END IF;
                        bahtTH := CONCAT(bahtTH, (SELECT Text FROM convert_num_th_rank WHERE Id = ((LENGTH(decVal) - i) - 1) LIMIT 1));
                    END IF;
                    i := i + 1;
                END LOOP;
                bahtTH := CONCAT(bahtTH,'สตางค์');
            END IF;
        END IF;

        RETURN bahtTH;
    END;
    $BODY$
    LANGUAGE plpgsql VOLATILE COST 100;
    """)

    # สร้างและเติมข้อมูลตารางสำหรับภาษาอังกฤษ
    cr.execute("""
    CREATE TABLE IF NOT EXISTS convert_num_en_num (
        Id integer PRIMARY KEY,
        Text varchar(255)
    );
    """)
    cr.execute("""
    INSERT INTO convert_num_en_num (Id, Text) VALUES
    (0, 'Zero'), (1, 'One'), (2, 'Two'), (3, 'Three'), (4, 'Four'),
    (5, 'Five'), (6, 'Six'), (7, 'Seven'), (8, 'Eight'), (9, 'Nine')
    ON CONFLICT (Id) DO NOTHING;
    """)

    cr.execute("""
    CREATE TABLE IF NOT EXISTS convert_num_en_rank (
        Id integer PRIMARY KEY,
        Text varchar(255)
    );
    """)
    cr.execute("""
    INSERT INTO convert_num_en_rank (Id, Text) VALUES
    (0, ''), (1, 'Ten'), (2, 'Hundred'), (3, 'Thousand'), (4, 'Ten Thousand'), 
    (5, 'Hundred Thousand'), (6, 'Million'), (9, 'Billion')
    ON CONFLICT (Id) DO NOTHING;
    """)

    # สร้างฟังก์ชัน convert_num_en
    cr.execute("""
    CREATE OR REPLACE FUNCTION public.convert_num_en(
        number numeric,
        currency_id integer)
        RETURNS text
        LANGUAGE plpgsql
        COST 100
        VOLATILE PARALLEL UNSAFE
    AS $BODY$
        declare
          num_words varchar default '';
          result_text varchar default '';
          integer_num varchar default '';

          i integer default 1;
          num integer default 0;
          num_len integer default 0 ;
          num_segment_len integer default 0 ;
          low_indx integer default 0 ;
          mid_indx integer default 0 ;

          num_text varchar default '';
          tmp_text varchar default '';
          num_segment varchar default '';
          delimeter varchar default '';

          unit_label varchar default '';
          sub_label varchar default '';

          begin
            begin
              select 
				coalesce(currency_unit_label->>'en_US', 'Baht'),
				coalesce(currency_subunit_label->>'en_US', 'Satang')
				into unit_label, sub_label
				from res_currency
				where id = currency_id;
            end;

            begin
              num_words = '';

              loop
                result_text = '';
                mid_indx = 0;

                integer_num = split_part(cast(number as text), '.', i);
                num_len = length(integer_num);

                while( num_len > 0 ) loop
                  tmp_text = '';
                  low_indx = 0 ;

                  num_segment = ltrim(substring(integer_num, num_len - 2, 3));
                  num_segment_len = length(num_segment) ;

                  while( num_segment_len > 0 ) loop
                    num = cast(substring(num_segment, num_segment_len, 1) as integer);
                    low_indx = low_indx + 1 ;
                    if low_indx = 2 then
                      if num = 1 then
                        num = cast(substring(num_segment, num_segment_len, 2) as integer);
                        case num
                          when 10 then num_text = 'Ten';
                          when 11 then num_text = 'Eleven';
                          when 12 then num_text = 'Twelve';
                          when 13 then num_text = 'Thirteen';
                          when 14 then num_text = 'Fourteen';
                          when 15 then num_text = 'Fifteen';
                          when 16 then num_text = 'Sixteen';
                          when 17 then num_text = 'Seventeen';
                          when 18 then num_text = 'Eighteen';
                          when 19 then num_text = 'Nineteen';
                          else num_text = '';
                        end case;
                      else
                        case num
                          when 2 then num_text = 'Twenty';
                          when 3 then num_text = 'Thirty';
                          when 4 then num_text = 'Forty';
                          when 5 then num_text = 'Fifty';
                          when 6 then num_text = 'Sixty';
                          when 7 then num_text = 'Seventy';
                          when 8 then num_text = 'Eighty';
                          when 9 then num_text = 'Ninety';
                          else num_text = '';
                        end case;
                      end if ;
                    else
                      case num
                        when 1 then num_text = 'One';
                        when 2 then num_text = 'Two';
                        when 3 then num_text = 'Three';
                        when 4 then num_text = 'Four';
                        when 5 then num_text = 'Five';
                        when 6 then num_text = 'Six';
                        when 7 then num_text = 'Seven';
                        when 8 then num_text = 'Eight';
                        when 9 then num_text = 'Nine';
                        else num_text = '';
                      end case;
                    end if;

                    case low_indx
                      when 3 then
                        if tmp_text ='' then
                          delimeter = ' Hundred ';
                        else
                          delimeter = ' Hundred and ' ;
                        end if;
                      when 2 then
                        if tmp_text ='' then
                          delimeter = '';
                        else
                          delimeter = '-' ;
                        end if;
                      else delimeter = '';
                    end case;

                    if not num_text = '' then
                      if num between 10 and 20 then
                        tmp_text = num_text;
                      else
                        tmp_text = concat(num_text, delimeter, tmp_text);
                      end if;
                    end if;

                    num_segment_len = num_segment_len - 1 ;
                  end loop;

                  case mid_indx
                    when 1 then delimeter = 'Thousand';
                    when 2 then delimeter = 'Million';
                    when 3 then delimeter = 'Billion';
                    when 4 then delimeter = 'Trillion';
                    else delimeter = '';
                  end case;

                  if not tmp_text = '' then
                    tmp_text = concat(tmp_text, ' ', delimeter);
                  end if;

                  if result_text = '' then
                    result_text = tmp_text;
                  else
                    result_text = concat(tmp_text, ', ', result_text);
                  end if;

                  mid_indx = mid_indx + 1;
                  num_len = num_len - 3;
                end loop;

                if i = 1 then
                  num_words = concat(result_text, unit_label);
                else
                  if result_text = '' then
                    num_words = concat(num_words, ' Only');
                  else
                    num_words = concat(num_words, ' and ', rtrim(result_text), ' ', sub_label) ;
                  end if;
                end if;

                i = i + 1 ;
                exit when i = 3 ;
              end loop;

              if number = 0 then
                num_words = concat('Zero ', num_words) ;
              end if;
              return num_words ;
            end;
          end;
    $BODY$;
    """)

    cr.commit()
