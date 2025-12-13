import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import base64 as b64
import deflate as df
import binascii
import struct
import time
import itertools
from itertools import chain,repeat
import json
import qrcode
import base64 as b64
import math
k=0
# version  v40.7.11
# debug log:
# v40.7.7: added data inspections
# v40.7.8 added other stuff on the side
# v40.7.9: added rle encoding unfinished
# v40.7.10.1: finished rle encoding
# v40.7.11: i finished the program
instruction_set={0x1: ('LDI',2),
                 0x2: ('MOV',2),
                 0x3: ('ADD',3),
                 0x4: ('SUB',3),
                 0x5: ('MUL',3),
                 0x6: ('SCR',2),
                 0x7: ('AND',3),
                 0x8: ('BOR',3),
                 0x9: ('NOT',3),
                 0xa: ('XOR',3),
                 0xb: ('BEZ',2),
                 0xc: ('REP',1),
                 0xd: ('HLT',0),
                 0xe: ('CMP',3),
                 0xf: ('EOL',0)}

EXTENDED_ENCODING = 'iso-8859-1'

tup_list = []
full = []
selection_map = {} 

for s in range(1, 9):
    for sub in range(1, 9):
        for div in range(1, 9):
            tup = (s, sub, div)
            tup_list.append(tup)
            display_str = f'Section {s}, Subsection {sub}, Division {div}'
            full.append(display_str)
            selection_map[display_str] = tup 

root = tk.Tk()
root.title("hugememory tools")
root.geometry("800x600")
root.config(bg='SystemButtonFace') 

full_memory_bytes = b''
current_section_bytes = [] 
a = 0
b = 0
l = (1, 1, 1) 
combo_var = tk.StringVar()

root.grid_rowconfigure(1, weight=1)  
root.grid_columnconfigure(0, weight=1) 
root.grid_columnconfigure(1, weight=1) 
root.config(bg='black')



sync_in_progress = False
expected_length = 256

def bytes_to_display_format(byte_data, text_widget=None):
    hex_lines = []
    bytes_per_line = 16
    
    placeholder_tag = 'placeholder'
    if text_widget:
        text_widget.tag_configure(placeholder_tag)
        text_widget.config(state=tk.NORMAL)
        text_widget.delete('1.0', tk.END)

    for i in range(0, len(byte_data), bytes_per_line):
        line_bytes = byte_data[i:i+bytes_per_line]
        hex_line = ' '.join([f"{byte:02X}" for byte in line_bytes])
        hex_lines.append(hex_line)
        
    if text_widget:
        for i in range(0, len(byte_data), bytes_per_line):
            line_bytes = byte_data[i:i+bytes_per_line]
            for byte in line_bytes:
                if 32 <= byte <= 126 or (byte >= 160):
                    char = bytes([byte]).decode(EXTENDED_ENCODING)
                    text_widget.insert(tk.END, char)
                else:
                    text_widget.insert(tk.END, '.', placeholder_tag) 
            text_widget.insert(tk.END, '\n')
        
        text_widget.edit_modified(False)
        return '\n'.join(hex_lines), None
    
    text_lines = []
    for i in range(0, len(byte_data), bytes_per_line):
        line_bytes = byte_data[i:i+bytes_per_line]
        text_line = ""
        for byte in line_bytes:
                if 32 <= byte <= 126 or (byte >= 160):
                     text_line += bytes([byte]).decode(EXTENDED_ENCODING)
                else:
                    text_line += '.'
        text_lines.append(text_line)
    return '\n'.join(hex_lines), '\n'.join(text_lines)

def sync_hex_to_text(event=None):
    global sync_in_progress, current_section_bytes
    if sync_in_progress or not hex_display.edit_modified():
        return
    
    sync_in_progress = True
    try:
        current_hex_str = hex_display.get('1.0', tk.END).strip()
        cleaned_hex_str = current_hex_str.replace(' ', '').replace('\n', '')
        
        if not cleaned_hex_str:
            text_display.delete('1.0', tk.END)
            current_section_bytes = []
            return

        if len(cleaned_hex_str) % 2 == 0:
            raw_bytes = binascii.unhexlify(cleaned_hex_str)
            current_section_bytes = list(raw_bytes)
            
            bytes_to_display_format(raw_bytes, text_widget=text_display)
            
    except binascii.Error:
        pass
    except ValueError:
        pass
    finally:
        hex_display.edit_modified(False)
        sync_in_progress = False


def sync_text_to_hex(event=None):
    global sync_in_progress, current_section_bytes
    if sync_in_progress or not text_display.edit_modified():
        return

    sync_in_progress = True
    try:
        new_bytes_list = []
        char_index = '1.0'
        byte_pos = 0

        while text_display.compare(char_index, "<", tk.END):
            if len(new_bytes_list) >= expected_length:
                break
                
            char = text_display.get(char_index, f"{char_index}+1c")
            
            if char == '\n':
                char_index = text_display.index(f"{char_index}+1c")
                continue

            if 'placeholder' in text_display.tag_names(char_index):
                new_bytes_list.append(0x00)
            else:
                try:
                    byte_val = ord(char.encode(EXTENDED_ENCODING, errors='strict'))
                    new_bytes_list.append(byte_val)
                except UnicodeEncodeError:
                    new_bytes_list.append(0x00) 

            char_index = text_display.index(f"{char_index}+1c")
            byte_pos += 1
            
        while len(new_bytes_list) < expected_length:
            new_bytes_list.append(0x00)
            
        new_bytes_list = new_bytes_list[:expected_length]
        raw_bytes = bytes(new_bytes_list)
        current_section_bytes = new_bytes_list[:]

        hex_output, _ = bytes_to_display_format(raw_bytes)
        
        hex_display.config(state=tk.NORMAL)
        hex_display.delete('1.0', tk.END)
        hex_display.insert('1.0', hex_output)
        hex_display.edit_modified(False)
        
    except Exception:
        pass
    finally:
        text_display.edit_modified(False)
        sync_in_progress = False

# There used to be a class here but i realized it would make l not global
def selection_changed(event):
    selected_option = combo_var.get()
    global l
    l = selection_map.get(selected_option, (1, 1, 1)) 

def on_scroll(*args):
    hex_display.yview(*args)
    text_display.yview(*args)

def get_mem():
    global l, full_memory_bytes, a, b, current_section_bytes
    global sync_in_progress
    was_syncing = sync_in_progress
    sync_in_progress = True

    try:
        hex_display.config(state=tk.NORMAL)
        text_display.config(state=tk.NORMAL)
        
        input_data = b64_input_field.get('1.0', tk.END).strip()
        compressed_data = b64.b64decode(input_data)
        full_memory_bytes = df.deflate_decompress(compressed_data, originalsize=131075)

        s, sub, div = l
        a = (s-1) * 16384 + (sub-1) * 2048 + (div-1) * 256
        b = a + 256

        section_bytes = full_memory_bytes[a:b]
        
        
        current_section_bytes = list(section_bytes)

        
        hex_output, _ = bytes_to_display_format(section_bytes, text_widget=text_display)
        hex_display.delete('1.0', tk.END)
        hex_display.insert('1.0', hex_output)
        hex_display.edit_modified(False)
        
        status_bar.config(text=f"Offset(h): {a:X} (Encoding: {EXTENDED_ENCODING})")

    except b64.binascii.Error as e:
        messagebox.showerror("Input Error", "The text provided is not a valid Base64 encoded string.")
    except IndexError as e:
        messagebox.showerror("Indexing Error", f"Cannot find the requested memory section. Details: {e}")
    except Exception as e:
        error_name = type(e).__name__
        messagebox.showerror("Fatal Error", f"A {error_name} occurred during decompression: {e}")
    finally:
        sync_in_progress = was_syncing
        hex_display.config(state=tk.NORMAL)
        text_display.config(state=tk.NORMAL)


def package_mem():
    global full_memory_bytes, a, b, current_section_bytes

    edited_bytes_segment = bytes(current_section_bytes)
    
    try:
        if len(edited_bytes_segment) != expected_length:
             raise ValueError(
                f'Memory input for division should be {expected_length} bytes long.'
            )

        if not full_memory_bytes:
             raise RuntimeError("Must load memory with 'get memory' first.")
             
        temp_byte_array = bytearray(full_memory_bytes)
        temp_byte_array[a:b] = edited_bytes_segment 
        full_memory_bytes = bytes(temp_byte_array)

        compressed_k = df.deflate_compress(data=full_memory_bytes, compresslevel=9)
        base64_j = b64.b64encode(compressed_k).decode()

        b64_input_field.delete('1.0', tk.END)
        b64_input_field.insert('1.0', base64_j)
        messagebox.showinfo("Success", "Memory packaged and placed in the input field.")

    except Exception as e:
         error_name = type(e).__name__
         messagebox.showerror("Packaging Error", f"An error occurred during packaging: {e}")

def load_file_to_b64():
    """Opens a file dialog, reads the file, compresses it, and populates the B64 input field."""
    file_path = filedialog.askopenfilename(
        title="Select File to Load",
        filetypes=[("All files", "*.*"), ("Text files", "*.txt"), ("Binary files", "*.bin")]
    )
    
    if not file_path:
        return

    try:
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        
        compressed_k = df.deflate_compress(data=file_bytes, compresslevel=9)
        base64_j = b64.b64encode(compressed_k).decode()

        b64_input_field.delete('1.0', tk.END)
        b64_input_field.insert('1.0', base64_j)
        
        status_bar.config(text=f"Loaded file '{file_path}' into Base64 input field.")
        messagebox.showinfo("Success", f"File '{file_path}' loaded and converted to Base64.")

    except Exception as e:
        error_name = type(e).__name__
        messagebox.showerror("File Error", f"A {error_name} occurred during file processing: {e}")

# --- UI Layout ---

int16_t='ASD' # I put debug values here and i still havent deleted it
int32_t='DSA'
int64_t='ASD'
unix_t='DSA'
float64_t='ASD'
labelint16_var = tk.StringVar(root, value="int16: N/A")
labelint32_var = tk.StringVar(root, value="int32: N/A")
labelint64_var = tk.StringVar(root, value="int64: N/A")
labelunix_var = tk.StringVar(root, value="Unix stamp: N/A")
labelfloat64_var = tk.StringVar(root, value="float64: N/A")
label_disassembly_var=tk.StringVar(root,value='aaaaaaa')


def get_selected():
    m = "int16: N/A"
    n = "Unix stamp: N/A"
    o = "int32: N/A"
    p = "int64: N/A"
    q = "float64: N/A"

    try:
        start, end = hex_display.tag_ranges(tk.SEL)
        display_hex_selected = hex_display.get(start, end)
        j = display_hex_selected.replace(' ', '').replace('\n', '')

        if not j:
            return (m, n, o, p, q)
            
        bytes_selected = bytes.fromhex(j)
        length = len(bytes_selected)
        


        if length <= 2:
            temp_bytes = bytes_selected.ljust(2, b'\x00')
            m = 'int16: ' + str(int.from_bytes(temp_bytes, byteorder='big', signed=False))

        if length >= 1:
            temp_bytes_unix = bytes_selected[:4].ljust(4, b'\x00')
            unix_time = struct.unpack('>I', temp_bytes_unix)[0]
            time_local = time.localtime(unix_time)
            str_time = time.strftime('%Y/%m/%d %H:%M:%S', time_local)
            n = 'Unix stamp: ' + str_time
        
        if length >= 1:
            temp_bytes_32 = bytes_selected[:4].ljust(4, b'\x00')
            o = 'int32: ' + str(int.from_bytes(temp_bytes_32, byteorder='big', signed=False))

        if length >= 1:
            temp_bytes_64 = bytes_selected[:8].ljust(8, b'\x00')
            p = 'int64: ' + str(int.from_bytes(temp_bytes_64, byteorder='big', signed=False))

        if length >= 8:
            temp_bytes_float64 = bytes_selected[:8].rjust(8, b'\x00') 
            q = f'float64: {struct.unpack(">d", temp_bytes_float64)[0]}'
            #Sadly i have to use big endian

    except ValueError:
        m = n = o = p = q = "Error/N/A"
    except struct.error:
        m = n = o = p = q = "Error/N/A"

    return (m, n, o, p, q)
main_frame=tk.Frame(root,bg='black',height=100,width=700)
main_frame.grid(row=1, column=0, sticky='nsew')
main_frame.configure(bg='black')

main_frame.grid_rowconfigure(0, weight=1)
main_frame.grid_columnconfigure(0, weight=3) 
main_frame.grid_columnconfigure(1, weight=1) 
hex_display = tk.Text(main_frame, wrap=tk.NONE, undo=True, maxundo=-1, state=tk.NORMAL,bg="#802783")

hex_display.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
hex_display.bind('<<Modified>>',sync_hex_to_text)
def disassembly(hex_widget):
    try:
        start, end = hex_widget.tag_ranges(tk.SEL)
        display_hex_selected = hex_widget.get(start, end)
        j = display_hex_selected.replace(' ', '').replace('\n', '')
        bytes_selected = bytes.fromhex(j)
        length = len(bytes_selected)

        fully_working_command = ''
        if length and length % 8 == 0:
            offset = 0
            while offset < length:
                name, op1, op2, op3 = struct.unpack('>HHHH', bytes_selected[offset:offset+8])
                c = name
                c_val = c & 0xf
                if c_val == 0:
                    offset += 8
                    continue
                instr_name, operands = instruction_set[c_val]
                fully_working_command += (instr_name + ' ')
                if operands >= 1:
                    fully_working_command += str(op1) + ' '
                if operands >= 2:
                    fully_working_command += str(op2) + ' '
                if operands >= 3:
                    fully_working_command += str(op3) + ' '
                fully_working_command += '\n'
                offset += 8

        # Show result in the UI label and the disassembly text box
        if fully_working_command:
            label_disassembly_var.set(fully_working_command.strip())
            try:
                disassembly_text.config(state=tk.NORMAL)
                disassembly_text.delete('1.0', tk.END)
                disassembly_text.insert(tk.END, fully_working_command)
                disassembly_text.config(state=tk.DISABLED)
            except Exception:
                pass
        else:
            no_msg = 'No disassembly (selection empty or length not multiple of 8)'
            label_disassembly_var.set(no_msg)
            try:
                disassembly_text.config(state=tk.NORMAL)
                disassembly_text.delete('1.0', tk.END)
                disassembly_text.insert(tk.END, no_msg)
                disassembly_text.config(state=tk.DISABLED)
            except Exception:
                pass

        return fully_working_command
    except Exception as e:
        label_disassembly_var.set(f'Error: {type(e).__name__}: {e}')
        return None
labelint16_var=tk.StringVar(root)
labelint32_var=tk.StringVar(root)
labelint64_var=tk.StringVar(root)
labelunix_var=tk.StringVar(root)
labelfloat64_var=tk.StringVar(root)
def update_text():

    results_tuple = get_selected() 
    
    labelint16_var.set(results_tuple[0])
    labelint32_var.set(results_tuple[2])
    labelint64_var.set(results_tuple[3])
    labelunix_var.set(results_tuple[1])
    labelfloat64_var.set(results_tuple[4])
control_frame = tk.Frame(root, pady=10, bg='SystemButtonFace')
control_frame.grid(row=0, column=0,columnspan=8, sticky='ew') 
control_frame.configure(bg='black')


def rle_encode():
    start_time_us = time.perf_counter_ns() // 1000
    global full_memory_bytes # Still need this global for the input data

    debug_print1_time = time.perf_counter_ns() // 1000 - start_time_us
    print(f"DEBUGNO {debug_print1_time} : Input raw binary length: {len(full_memory_bytes)}") 

    data_raw_binary = full_memory_bytes # Renamed variable for clarity

    rle_data = b''
    for byte, group in itertools.groupby(data_raw_binary):
        count = len(list(group))
        while count > 0:
            chunk_size = min(count, 255)
            rle_data += bytes([chunk_size, byte])
            count -= chunk_size
    
    debug_print2_time = time.perf_counter_ns() // 1000 - start_time_us
    print(f"DEBUGNO {debug_print2_time}: RLE encoded data length: {len(rle_data)}")


    with open(r'C:\Users\Kraeon\cm2-tools\config_filenos.json', 'r') as f:
        config_data = json.load(f) # its json cuz yes
    
    current_k = int(config_data['fileno'])
    
    
    filename = f'encoded_HxDHmem_v40.7.13fileno{current_k}.cmh'
    with open(filename, 'wb') as f:
        f.write(rle_data)
    info_print_2_time=time.perf_counter_ns()//1000-start_time_us
    print(F'INFONO {info_print_2_time}: Wrote file')
    qr=qrcode.QRCode(
        version=40,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=4
    )
    qr.add_data(b64.b64encode(rle_data).decode('ascii'))
    qr.make(fit=True)
    image_name=filename.replace('.cmh','.png')
    img=qr.make_image(fill_color="#220043",back_color='#DDFFBC')
    img.save(image_name)
   
    next_k = current_k + 1
    data_save = {
        "fileno": str(next_k)
    }
    with open('config_filenos.json', 'w') as f:
        json.dump(data_save, f, indent=4)
    info_print_3_time=time.perf_counter_ns()//1000-start_time_us
    print(F'INFONO {info_print_3_time}: Wrote JSON')
    INFO_time = time.perf_counter_ns() // 1000 - start_time_us
    print(f"INFONO {INFO_time}: Wrote {len(rle_data)} bytes to {filename}")


def rle_decode():
    global full_memory_bytes
    
    
    encoded_data = full_memory_bytes 

    if not encoded_data:
        messagebox.showerror('Decode Error', 'No encoded data in memory to decode.')
        return

    
    decoded_bytes = b''
    for i in range(0, len(encoded_data), 2):
        try:
            count = encoded_data[i]       
            byte_value = encoded_data[i+1] 
            
           
            decoded_bytes += bytes([byte_value]) * count
            
        except IndexError:
            messagebox.showerror('Decode Error', f'RLE data terminated abruptly at index {i}. Data might be corrupt.')
            break
    

    expected_length = 131072
    actual_length = len(decoded_bytes)

    if actual_length == expected_length:
        
        full_memory_bytes = decoded_bytes 

        try:    
            hex_output, _ = bytes_to_display_format(full_memory_bytes, text_widget=text_display)
            hex_display.delete('1.0', tk.END)
            hex_display.insert('1.0', hex_output)
            hex_display.edit_modified(False)
            print(f"Successfully decoded and displayed {actual_length} bytes.")

        except Exception as E:
            messagebox.showerror('Unexpected Error',f'{type(E).__name__} happened: {E.__cause__}')
            
    else:
        error_msg = f"Decode failed: Expected {expected_length} bytes but got {actual_length} bytes."
        messagebox.showerror('Decode Error', error_msg)


def save_selection_as_image(event=None):
    """Save the selected bytes in `hex_display` to an RGB image.

    Group bytes into (R,G,B) triples. If length % 3 != 0, pad with 0x00.
    Image width is chosen as ceil(sqrt(num_pixels)) and height computed accordingly.
    """
    try:
        # Try hex_display first; if empty, look in other text widgets (user might have focus elsewhere)
        start_end = hex_display.tag_ranges(tk.SEL)
        selected_widget = hex_display
        if not start_end:
            for w in (text_display, b64_input_field):
                tr = w.tag_ranges(tk.SEL)
                if tr:
                    start_end = tr
                    selected_widget = w
                    break

        if not start_end:
            messagebox.showinfo('Save Image', 'No selection. Please select some bytes in the hex pane and ensure it has focus.')
            return

        start, end = start_end
        display_hex_selected = selected_widget.get(start, end)
        j = display_hex_selected.replace(' ', '').replace('\n', '')
        if not j:
            messagebox.showinfo('Save Image', 'Selection is empty.')
            return

        data = bytes.fromhex(j)
        # pad to multiple of 3
        if len(data) % 3 != 0:
            data += b'\x00' * (3 - (len(data) % 3))

        pixels = [tuple(data[i:i+3]) for i in range(0, len(data), 3)]
        num_pixels = len(pixels)
        width = math.ceil(math.sqrt(num_pixels))
        height = math.ceil(num_pixels / width)

        try:
            from PIL import Image
        except Exception:
            messagebox.showerror('Pillow required', 'Pillow is required for image export. Install it with "pip install pillow".')
            return

        img = Image.new('RGB', (width, height), (0, 0, 0))
        px = img.load()
        for idx, color in enumerate(pixels):
            x = idx % width
            y = idx // width
            px[x, y] = color

        save_path = filedialog.asksaveasfilename(defaultextension='.png', filetypes=[('PNG Image', '*.png'), ('All files', '*.*')])
        if not save_path:
            return

        img.save(save_path)
        messagebox.showinfo('Save Image', f'Saved image to {save_path}')

    except Exception as e:
        messagebox.showerror('Save Image Error', f'{type(e).__name__}: {e}')


def load_image_to_hex(event=None):
    """Load an image file and decode its pixels into bytes (row-major left-to-right, top-to-bottom).

    Each pixel contributes three bytes (R,G,B). The resulting byte stream is placed into the hex display
    and the text view is synchronized.
    """
    try:
        try:
            status_bar.config(text='Importing image...')
        except Exception:
            pass
        try:
            from PIL import Image
        except Exception:
            messagebox.showerror('Pillow required', 'Pillow is required for image import. Install it with "pip install pillow".')
            return

        path = filedialog.askopenfilename(title='Open image', filetypes=[('Image files', '*.png;*.jpg;*.bmp;*.gif'), ('All files', '*.*')])
        if not path:
            return

        img = Image.open(path).convert('RGB')
        pixels = list(img.getdata())
        data = bytearray()
        for r, g, b in pixels:
            data.extend((r, g, b))

        # Trim trailing zeros? Leave as-is; user can edit
        raw_bytes = bytes(data)
        # update the displays
        hex_output, _ = bytes_to_display_format(raw_bytes)

        hex_display.config(state=tk.NORMAL)
        hex_display.delete('1.0', tk.END)
        hex_display.insert('1.0', hex_output)
        hex_display.edit_modified(False)

        # also populate text_display via existing helper
        bytes_to_display_format(raw_bytes, text_widget=text_display)

        messagebox.showinfo('Import Image', f'Imported {len(raw_bytes)} bytes from image {path}')

    except Exception as e:
        messagebox.showerror('Import Image Error', f'{type(e).__name__}: {e}')
    finally:
        try:
            status_bar.config(text='Ready.')
        except Exception:
            pass


def save_full_memory_as_image(event=None):
    """Save the entire `full_memory_bytes` buffer as an RGB image.

    Default width is 256 unless the user selects a different width via a prompt.
    """
    try:
        if not full_memory_bytes:
            messagebox.showinfo('Save Image', 'No memory loaded. Use Get Memory first.')
            return

        # Ask for preferred width (default 256)
        width = simpledialog.askinteger('Image Width', 'Enter desired image width in pixels:', initialvalue=256, minvalue=1)
        if width is None:
            return

        data = bytes(full_memory_bytes)
        # pad to multiple of 3
        if len(data) % 3 != 0:
            data += b'\x00' * (3 - (len(data) % 3))

        pixels = [tuple(data[i:i+3]) for i in range(0, len(data), 3)]
        num_pixels = len(pixels)
        height = (num_pixels + width - 1) // width

        try:
            from PIL import Image
        except Exception:
            messagebox.showerror('Pillow required', 'Pillow is required for image export. Install it with "pip install pillow".')
            return

        img = Image.new('RGB', (width, height), (0, 0, 0))
        px = img.load()
        for idx, color in enumerate(pixels):
            x = idx % width
            y = idx // width
            px[x, y] = color

        save_path = filedialog.asksaveasfilename(defaultextension='.png', filetypes=[('PNG Image', '*.png'), ('All files', '*.*')], title='Save full memory as image')
        if not save_path:
            return

        img.save(save_path)
        messagebox.showinfo('Save Image', f'Saved full memory to {save_path} ({width}×{height})')

    except Exception as e:
        messagebox.showerror('Save Full Memory Error', f'{type(e).__name__}: {e}')
    




label_frame = tk.Frame(main_frame)
label_frame.grid(row=1, column=0, sticky='ew') 
label_frame.configure(bg='black')



label_int16 = tk.Label(label_frame, textvariable=labelint16_var, anchor='w',fg='white',bg='black')
label_int32 = tk.Label(label_frame, textvariable=labelint32_var, anchor='w',fg='white',bg='black')
label_int64 = tk.Label(label_frame, textvariable=labelint64_var, anchor='w',fg='white',bg='black')
label_unix = tk.Label(label_frame, textvariable=labelunix_var, anchor='w',fg='white',bg='black')
label_float64 = tk.Label(label_frame, textvariable=labelfloat64_var, anchor='w',fg='white',bg='black')


label_int16.grid(row=0, column=0, sticky='ew', padx=5, pady=2)
label_int32.grid(row=1, column=0, sticky='ew', padx=5, pady=2)
label_int64.grid(row=2, column=0, sticky='ew', padx=5, pady=2)
label_unix.grid(row=3, column=0, sticky='ew', padx=5, pady=2)
label_float64.grid(row=4, column=0, sticky='ew', padx=5, pady=2)

# Disassembly output label (shows assembler output for the selected bytes)
label_disasm = tk.Label(label_frame, textvariable=label_disassembly_var, anchor='w', fg='white', bg='black', justify='left', wraplength=400)
label_disasm.grid(row=5, column=0, sticky='ew', padx=5, pady=2)

# Read-only multi-line disassembly view (for longer output)
disassembly_text = tk.Text(main_frame, height=6, wrap=tk.WORD, state=tk.DISABLED, bg='#111', fg='white')
disassembly_text.grid(row=2, column=0, columnspan=2, sticky='ew', padx=5, pady=2)
# Disassembly output label (shows assembler output for the selected bytes)
label_disasm = tk.Label(label_frame, textvariable=label_disassembly_var, anchor='w', fg='white', bg='black', justify='left', wraplength=400)
label_disasm.grid(row=5, column=0, sticky='ew', padx=5, pady=2)




combo_box = ttk.Combobox(control_frame, textvariable=combo_var, values=full, state='readonly', width=50)
combo_box.grid(row=0, column=0, padx=10, pady=5, sticky='w')
combo_box.bind("<<ComboboxSelected>>", selection_changed)
combo_box.set(full)

get_mem_button = tk.Button(control_frame, text="Get Memory", command=get_mem)
get_mem_button.grid(row=0, column=1, padx=5, pady=5)
package_mem_button = tk.Button(control_frame, text="Package Memory", command=package_mem)
package_mem_button.grid(row=0, column=2, padx=5, pady=5)
load_file_button = tk.Button(control_frame, text="Load File to B64", command=load_file_to_b64)
load_file_button.grid(row=0, column=3, padx=5, pady=5)
button_print_selected=tk.Button(control_frame,text='Inspect data',command=update_text)
button_print_selected.grid(row=0,column=4,padx=5,pady=5)
rle_encode_button=tk.Button(control_frame,text='Save file compressed',command=rle_encode)
rle_encode_button.grid(row=0,column=5,padx=5,pady=5)
rle_decode_button=tk.Button(control_frame,text='Decode memory as RLE',command=rle_decode)
rle_decode_button.grid(row=0,column=6,padx=5,pady=5)
button_disassemble=tk.Button(control_frame,text='Disassemble selected text',command= lambda: disassembly(hex_display))
button_disassemble.grid(row=0,column=7,padx=5,pady=5)
save_image_button = tk.Button(control_frame, text='Save Selection as Image', command=save_selection_as_image)
save_image_button.grid(row=0, column=8, padx=5, pady=5)
load_image_button = tk.Button(control_frame, text='Load Image -> Hex', command=load_image_to_hex)
load_image_button.grid(row=0, column=9, padx=5, pady=5)
# Button to save entire memory as image
save_full_image_button = tk.Button(control_frame, text='Save Full Memory as Image', command=save_full_memory_as_image)
save_full_image_button.grid(row=0, column=10, padx=5, pady=5)
# Keyboard shortcuts
root.bind('<Control-i>', save_selection_as_image)   # Ctrl+I to save selection as image
hex_display.bind('<Control-i>', save_selection_as_image)
root.bind('<Control-Shift-d>', load_image_to_hex)  # Ctrl+Shift+D to load image into hex
hex_display.bind('<Control-Shift-d>', load_image_to_hex)
root.bind('<Control-Shift-D>', load_image_to_hex)
hex_display.bind('<Control-Shift-D>', load_image_to_hex)
# Bind globally to catch variants regardless of widget focus
root.bind_all('<Control-Shift-d>', load_image_to_hex)
root.bind_all('<Control-Shift-D>', load_image_to_hex)
# Ctrl+Alt+I to save full memory as image
root.bind_all('<Control-Alt-i>', save_full_memory_as_image)
root.bind_all('<Control-Alt-I>', save_full_memory_as_image)
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_rowconfigure(1, weight=1)
text_display = tk.Text(root, wrap=tk.NONE, undo=True, maxundo=-1, state=tk.NORMAL,bg="#6B3A6D")
text_display.grid(row=1, column=1, padx=5, pady=5, sticky='ns')
text_display.bind('<<Modified>>', sync_text_to_hex)
text_display.bind('<Control-i>', save_selection_as_image)
text_display.bind('<Control-Shift-d>', load_image_to_hex)

v_scrollbar = ttk.Scrollbar(root, orient=tk.VERTICAL, command=on_scroll)
v_scrollbar.grid(row=1, column=2, sticky='ns', pady=5)

hex_display.configure(yscrollcommand=v_scrollbar.set)
text_display.configure(yscrollcommand=v_scrollbar.set)

b64_label = tk.Label(root, text="Base64 Input/Output (Full Save String):", bg='black',fg='white')
b64_label.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky='w')

b64_input_field = tk.Text(root, height=5, wrap=tk.WORD)
b64_input_field.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky='nsew')
root.grid_rowconfigure(3, weight=0)

status_bar = tk.Label(root, text="Ready.", bd=1, relief=tk.SUNKEN, anchor=tk.W, bg='black',fg='white')
status_bar.grid(row=4, column=0, columnspan=3, sticky='ew')

root.mainloop()
