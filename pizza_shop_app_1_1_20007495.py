# 20007495 Assessment Part 1.1
# Core imports and constants 
import os
import webbrowser
import json
import time
import tkinter as tk
from tkinter import Tk, ttk, messagebox
from datetime import datetime
from fpdf import FPDF


# Constants 

# Intitally full Ingredient supplies 
INGREDIENTS = {
    "dough": 5,
    "sauce": 5,
    "toppings": 5
}

""" As the inventory is full, shopping isn not needed. 
As the inventory replenishes within the order processing, no signal was reaching the generate shopping list module to trigger a log.
These will be used later on to solve this issue.
"""
SHOPPING_NEEDED = {
    "dough": False,
    "sauce": False,
    "toppings": False
}
# Maximum number of ingredients per item 
MAX_INGREDIENTS = 5

# Set the duration of each task to be referenced in the order processing and shop workflow simulation 
TASK_DURATIONS = {
    "register_order": 1,
    "cook_order": 1,
    "collect_order": 3,
    "shopping_list": 3
}

# Constants for file storage 
SESSION_FILE = "session_data_1_1.json"
PARTIAL_SELECTION_FILE = "partial_selection_1_1.json"

# Session management functions
# Time Complexity O(n) where n is size of orders dictionary 
# Space Complexity O(n) for serialization 
def save_session(orders, next_order_id, partial_selection=None):
    """ Handles atomic saving of session data with custom datetime serialization. 
    Uses a temporary file for atomic writing to tackle data corruption."""
    def custom_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    
    session_data = {"orders": orders, "next_order_id": next_order_id, "partial_selection": partial_selection}
    temp_file = f"{SESSION_FILE}.tmp"
    try:
        with open(temp_file, "w") as f:
            json.dump(session_data, f, default=custom_serializer)
        os.replace(temp_file, SESSION_FILE) # Atomic replacemnt 
    except Exception as e:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        messagebox.showerror("Session Save Error", f"Failed to save session: {e}")

# Time Complexity: O(n) for JSON parsing 
# Space Complexity: O(n) where n is file size
def load_session():
    """Loads and deserializaes session data with datetime parsing. 
    Handles corrupted files by creating a new session. """
    def custom_deserializer(dct):
        for key, value in dct.items():
            if isinstance(value, str) and value.endswith("Z") and "T" in value:
                try:
                    dct[key] = datetime.fromisoformat(value)
                except ValueError:
                    pass
        return dct

    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                return json.load(f, object_hook=custom_deserializer)
        except (json.JSONDecodeError, ValueError):
            messagebox.showerror(
                "Session Load Error",
                "The session data file is corrupted. Starting with a clean session.",
            )
            os.remove(SESSION_FILE)
    return {"orders": {}, "next_order_id": 1, "partial_selection": {}}

# PDF Generation Functions 
# Time Complexity O(n) where n is number of content lines
def generate_pdf(filename, content):
    """Utility function to generate a PDF."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in content:
        pdf.cell(200, 10, txt=line, ln=True, align='L')
    pdf.output(filename)

     # Cross-platform file opening
    try:
        # Attempt Windows-specific method
        if os.name == 'nt': 
            os.startfile(filename) 
    except (AttributeError, OSError):
        # Fallback to webbrowser for other platforms
        webbrowser.open(filename) 

# Order logging 
# Time Complexity O(n) where n is number of log entries
# Space Complexity O(n)
def order_updates_to_file(order_id, action):
    """Log order updates to a PDF file."""
    log_entries = []
   
   # If log file exists, read previous entries
    log_file = "order_log_1_1.json"
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            log_entries = json.load(f)

    # Append the new log entry
    log_entries.append({"order_id": order_id, "action": action, "timestamp": datetime.now().isoformat()})

    # Save back to JSON
    with open(log_file,  "w") as f:
        json.dump(log_entries, f, indent=4)

    # Regenerate the PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Order Log", ln=True, align='C')
    pdf.cell(200, 10, txt="", ln=True)  # Blank line
    for entry in log_entries:
        pdf.cell(200, 10, txt=f"Order {entry['order_id']} {entry['action']} at {entry['timestamp']}", ln=True, align='L')
    pdf.output("order_log_1_1.pdf") # Name of PDF

def get_icon_path():
    """Returns the absolute path to the icon file."""
    script_dir = os.path.dirname(os.path.abspath(__file__)) 
    icon_path = os.path.join(script_dir, "app_thumb.icns") # Prefer .ico but had issues with getting it to generate in macOS
    return icon_path

# Main Application Class
class PizzaShopApp:
    """ Managing UI and buisness logic. 
    Uses Model view controller-esc pattern with Tkinter for UI"""
    def __init__(self, root):
        self.root = root
        self.root.title("Pizza Shop Application")
        self.root.iconbitmap("app_thumb.icns") 
        self.replenishment_needed = False
        # print("Icon Path:", get_icon_path()) - TROUBLESHOOTING TOOL

        # Load session data i.e. window closed before an order is submitted, progress saved 
        session_data = load_session()
        self.orders = session_data["orders"]
        self.next_order_id = session_data["next_order_id"]
        self.partial_selection = session_data.get("partial_selection", {})

        self.create_widgets()
        self.restore_partial_selection()

    def show_error(self, message):
        self.error_label.config(text=message)
        self.error_label.after(4000, lambda: self.error_label.config(text="")) # Clear after 4 seconds

    def validate_quantity(self, value):
        # Validate quantity input to ensure it's always a number between 1-10
        if value == "":
            return False # Reject empty input 
        try:
            val = int(value) # Convert string to integar 
            if 1 <= val <= 10: 
                return True # Input is valid
            else:
            # Show error if out of range
                self.show_error("Please select a pizza quantity between 1 and 10")
                return False
        except ValueError:
            # Show an error if input is not a number
            self.show_error("Quantity must be a valid number")
            return False
        
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid()

        # UI Creation Methods 
        # Order Frame
        order_frame = ttk.LabelFrame(main_frame, text="Order")
        order_frame.grid(row=0, column=0, sticky="nsew")
        
        # Pizza Type Combobox 
        ttk.Label(order_frame, text="Pizza Type: ").grid(row=0, column=0, sticky="w")
        self.pizza_type_var = tk.StringVar(value="Select")
        self.pizza_type_combobox = ttk.Combobox(order_frame, textvariable=self.pizza_type_var, values=[ # Pizza types
            "Select", 
            "Chef Sagir's Special", 
            "Meat Feast", 
            "Vegetable", 
            "Margherita", 
            "Pepperoni", 
            "Vegetable (Vegan)", 
            "Margherita (Vegan)"
            ], state="readonly")
        self.pizza_type_combobox.grid(row=0, column=1, sticky="w")
        self.pizza_type_var.trace_add("write", self.save_partial_selection)

        # Dietary Checkbuttons (not in brief but added for fun, as seen in most food ordering systems)
        ttk.Label(order_frame, text="Dietary Requirements: ").grid(row=1, column=0, sticky="w")
        self.ve_var = tk.BooleanVar()
        ttk.Checkbutton(order_frame, text="VE", variable=self.ve_var, command=self.filter_pizzas).grid(row=1, column=1, sticky="w")
        self.vg_var = tk.BooleanVar()
        ttk.Checkbutton(order_frame, text="VG", variable=self.vg_var, command=self.filter_pizzas).grid(row=1, column=2, sticky="w")
        self.gf_var = tk.BooleanVar()
        ttk.Checkbutton(order_frame, text="GF", variable=self.gf_var, command=self.filter_pizzas).grid(row=1, column=3, sticky="w")

        # Pizza Size Combobox
        ttk.Label(order_frame, text="Size: ").grid(row=2, column=0, sticky="w")
        self.size_var = tk.StringVar(value="Select")
        self.size_combobox = ttk.Combobox(order_frame, textvariable=self.size_var, values=[ # Pizza sizes
            "Select", 
            "Small", 
            "Medium", 
            "Large"
            ], state="readonly")
        self.size_combobox.grid(row=2, column=1, sticky="w")
        self.size_var.trace_add("write", self.save_partial_selection)

        # Pizza Quantity Spinbox
        ttk.Label(order_frame, text="Quantity: ").grid(row=3, column=0, sticky="w")
        self.qty_var = tk.IntVar(value=1) # Defaults to 1 
        self.qty_spinbox = ttk.Spinbox(
            order_frame,
            from_=1, 
            to=10, 
            textvariable=self.qty_var, 
            width=5, 
            wrap=True, 
            validate='all', 
            validatecommand=(self.validate_quantity, '%P')
        )
        self.qty_spinbox.grid(row=3, column=1, sticky="w")
        self.qty_var.trace_add("write", self.save_partial_selection)
        
        # Add a generl error label in a visible location. This instead of messagebox.showerror("") to reduce UX interference 
        self.error_label = ttk.Label(order_frame, text="", foreground="cyan") # Initialises as "" to be reassigned later
        self.error_label.grid(row=5, column=0, columnspan=2)
        # Submit Order button 
        ttk.Button(order_frame, text="Submit Order", command=self.add_order).grid(row=4, column=0, columnspan=2)

        # Order Track Frame
        #  Columns to watch the status of the last placed order 
        self.track_frame = ttk.LabelFrame(main_frame, text="Order Track")
        self.track_frame.grid(row=0, column=1, rowspan=2,sticky="nsew")

        self.track_tree = ttk.Treeview(self.track_frame, columns=("Order Number", "Status"), show="headings")
        self.track_tree.heading("Order Number", text="Order Number")
        self.track_tree.heading("Status", text="Status")
        self.track_tree.grid(row=0, column=1, rowspan=2, sticky="nsew")

        # Order Management Frame
        # Buttons to Generate the shop's useful PDFs
        management_frame = ttk.LabelFrame(main_frame, text="Order Management")
        management_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")

        ttk.Button(management_frame, text="Show All Orders", command=self.show_orders).grid(row=0, column=0, sticky="w")
        ttk.Button(management_frame, text="Generate Shopping List PDF", command=self.generate_shopping_list).grid(row=0, column=1, sticky="w")
        ttk.Button(management_frame, text="Generate Favourites Report", command=self.generate_favourites_report).grid(row=0, column=2, sticky="w")
        ttk.Button(management_frame, text="Save and Quit", command=root.quit).grid(row=0, column=4, sticky="w")
    
    def filter_pizzas(self):
        """ Extra functionality """
        available_pizzas = ["Select"]
        if self.ve_var.get() and not self.vg_var.get(): # Cannot select both vegetarian and vegan 
            available_pizzas.extend(["Vegetable", "Margherita"])
        elif self.vg_var.get() and not self.ve_var.get():
            available_pizzas.extend(["Vegetable (Vegan)", "Margherita (Vegan)"]) 
        elif not self.ve_var.get() and not self.vg_var.get():
            available_pizzas.extend(["Meat Feast", "Vegetable", "Margherita", "Pepperoni"]) # All choices available as no dietary restrictions 

        if self.gf_var.get():
            # Safest bet is to custom order for Gluten free customers so call the store. \n new lines for easy viewing 
            messagebox.showinfo("Gluten-Free options", f"Thank you for your interest in Sagir's Pizza Shop.  \nWe are happy to accommodate Gluten-Free options. \nPlease call the branch at 01782732000 to order.") 

        self.pizza_type_combobox['values'] = available_pizzas
        self.pizza_type_var.set("Select")

    def save_partial_selection(self, *_):
        """ If the application is closed before submitting the order, aim to save their partial selection """
        partial_selection = {
            "pizza_type": self.pizza_type_var.get(),
            "size": self.size_var.get(),
            "quantity": self.qty_var.get()
        }
        save_session(self.orders, self.next_order_id, partial_selection)

    def restore_partial_selection(self):
        """ Retore partial selection once re-opened """
        if self.partial_selection:
            self.pizza_type_var.set(self.partial_selection.get("pizza_type", "Select"))
            self.size_var.set(self.partial_selection.get("size", "Select"))
            self.qty_var.set(self.partial_selection.get("quantity", 1))

    def add_order(self):
        pizza_type = self.pizza_type_var.get()
        size = self.size_var.get()
        quantity = self.qty_var.get()
        if not self.validate_quantity(quantity):
            return # Half order placement if validation fails 
        
        if pizza_type == "Select" or size == "Select":
            # The comboboxes default to user prompt "Select". This ensures they cannot proceed with an order without selecting from the acceptable lists
            self.show_error("Please select both Pizza Type and Size.")
            return
        
        order_id = self.next_order_id
        self.orders[order_id] = {
            "pizza_type": pizza_type,
            "size": size,
            "quantity": quantity,
            "status": "Registered",
            "time_registered": datetime.now(),
            "time_collected": None
        }
        self.next_order_id += 1 # Increment the next order by one so all submissions are unique and in order 
        save_session(self.orders, self.next_order_id)

        self.track_tree.insert("", "end", values=(order_id, "Registered"))
        messagebox.showinfo("Order Placed", f'Your order has been placed. Your order number is {order_id}.')

        # Start processing the order after it's registered
        self.process_order(order_id)

    # Helper function to update inventory 
    def update_inventory(self, pizza, action="decrement"):
            for ingredient, amount in pizza.items():
                if action == "decrement":
                    if INGREDIENTS[ingredient] < amount:
                        self.replenishment_needed = True 
                    INGREDIENTS[ingredient] -= amount
                elif action == "increment":
                    INGREDIENTS[ingredient] = min(MAX_INGREDIENTS, INGREDIENTS[ingredient] + amount)

    def process_order(self, order_id):
        """Process the order with smooth status changes."""
        try:
            # Step 1: Register - Status Registered
            self.update_status_in_tree(order_id, "Registered")
            self.orders[order_id]["status"] = "Registered"
            order_updates_to_file(order_id, "Registered")  # Log "Registered"
            
            # Using after for smooth transitions instead of time.sleep()
            self.root.after(TASK_DURATIONS["register_order"] * 1000, self.start_cooking, order_id)
            
             # Step 2: Check and update inventory 
            size = self.orders[order_id]["size"].lower()
            quantity = self.orders[order_id]["quantity"]
            if size == "small":
                pizza = {"dough": 1, "sauce": 1, "toppings": 2}
            elif size == "medium":
                pizza = {"dough": 2, "sauce": 1, "toppings": 3}
            elif size == "large":
                pizza = {"dough": 3, "sauce": 2, "toppings": 4}
            else:
                raise ValueError(f"Invalid size for order {order_id}")

            # Intra-order shopping requirement validation 
            for ingredient, amount in pizza.items():
                pizza[ingredient] *= quantity

            # Check inventory and handle replenishment
            insufficient_ingredients = []
            for ingredient, amount in pizza.items():
                if INGREDIENTS[ingredient] < amount:
                    insufficient_ingredients.append(ingredient)
                    SHOPPING_NEEDED[ingredient] = True # Flag for shopping list 

            if insufficient_ingredients:
                for ingredient in insufficient_ingredients:
                    self.replenish_inventory(ingredient)
                messagebox.showinfo(
                    "Inventory Replenished",
                    f"Not enough of {', '.join(insufficient_ingredients)}. Replenished to {MAX_INGREDIENTS}. Resuming order processing."
                )

            # Update inventory after potential replenishment
            self.update_inventory(pizza) 

        except Exception as e:
            messagebox.showerror("Process Error", f"Error processing order {order_id}: {str(e)}")
            self.update_status_in_tree(order_id, "Error")
            order_updates_to_file(order_id, "Error")  # Log "Error" 

    def start_cooking(self, order_id):
        """Starts the cooking phase after the register phase."""
        try:
            self.update_status_in_tree(order_id, "Cooking")
            self.orders[order_id]["status"] = "Cooking"
            order_updates_to_file(order_id, "Cooking")  # Log "Cooking"
            
            # After cooking, move to collection
            self.root.after(TASK_DURATIONS["cook_order"] * 1000, self.collect_order, order_id)
        except Exception as e:
            messagebox.showerror("Process Error", f"Error during cooking phase for order {order_id}: {str(e)}")
            self.update_status_in_tree(order_id, "Error")
            order_updates_to_file(order_id, "Error")  # Log "Error"
        
    def collect_order(self, order_id):
        """Collect the order after cooking is done."""
        try:
            self.update_status_in_tree(order_id, "Ready to Collect")
            self.orders[order_id]["status"] = "Ready to Collect"
            order_updates_to_file(order_id, "Ready to Collect")  # Log "Ready to Collect"
            
            # After collection, mark the order as collected
            self.root.after(TASK_DURATIONS["collect_order"] * 1000, self.finalise_order, order_id)
        except Exception as e:
            messagebox.showerror("Process Error", f"Error during collection phase for order {order_id}: {str(e)}")
            self.update_status_in_tree(order_id, "Error")
            order_updates_to_file(order_id, "Error")  # Log "Error"

    def finalise_order(self, order_id):
        """Finalise the order after collection and remove it from the tree."""
        try:
            # Mark the order as collected and update tree
            self.orders[order_id]["status"] = "Collected"
            self.update_status_in_tree(order_id, "Collected")
            order_updates_to_file(order_id, "Collected")  # Log "Collected"

            # Schedule removal of the order from the tree after 2 seconds
            self.root.after(2000, lambda: self.remove_from_tree(order_id))
            
        except Exception as e:
            messagebox.showerror("Process Error", f"Error finalising order {order_id}: {str(e)}")
            self.update_status_in_tree(order_id, "Error")
            order_updates_to_file(order_id, "Error")  # Log "Error"


    def replenish_inventory(self, ingredient):
        # Replenish the inventory of a specific ingredient and log it.
            current_amount = INGREDIENTS[ingredient]
            if current_amount <= 0: # Only replenish when at zero or below
                INGREDIENTS[ingredient] = MAX_INGREDIENTS
                return f"Replenished {ingredient} from {current_amount} to {MAX_INGREDIENTS}"
            return None
    
    def replenish_inventory_worker(self):
        while True:
            if self.replenishment_needed:
                for ingredient, amount in INGREDIENTS.items():
                    if amount <= 0:
                        self.replenish_inventory(ingredient) 
            self.replenishment_needed = False 
            time.sleep(1)       

    def remove_from_tree(self, order_id_to_remove):
        """Safely remove an order from the tree view."""
        try:
            # Convert order_id_to_remove to string to match tree values, or int if needed
            order_id_str = str(order_id_to_remove)
            print(f"Removing order {order_id_str} from tree...")

            for item in self.track_tree.get_children():
                # Adjust the index to the column where the order ID is located (0 is the first column)
                order_id_from_tree = str(self.track_tree.item(item)["values"][0])  # could use int() if necessary

                if order_id_from_tree == order_id_str:
                    self.track_tree.delete(item)
                    print(f"Order {order_id_str} removed from tree.")
                    break
            else:
                print(f"Order {order_id_str} not found in tree.")
        except Exception as e:
            print(f"Error removing from tree: {e}")

    """Management Frame Logic"""            
    def show_orders(self):
        # Create a new Toplevel window for displaying orders
        orders_window = tk.Toplevel(self.root)
        orders_window.title("All Orders")
        orders_window.geometry("400x400")  # Adjust as needed for your UI design
        orders_window.resizable(True, True)

        # Style configuration
        style = ttk.Style()
        style.configure("TLabel", font=("Helvetica", 12), padding=5)

        # Main container frame
        container = ttk.Frame(orders_window)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Scrollable area setup
        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Populate the scrollable frame with orders
        ttk.Label(scrollable_frame, text="Order Details", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=5)
        for order_id, details in self.orders.items():
            order_text = (
                f"Order ID: {order_id}\n"
                f"Quantity: {details['quantity']}\n"
                f"Pizza Type: {details['pizza_type']}\n"
                f"Status: {details['status']}\n"
                f"{'-' * 30}"
            )
            ttk.Label(scrollable_frame, text=order_text, justify="left", anchor="w").pack(fill="x", pady=5)

        # Close button
        close_button = ttk.Button(orders_window, text="Close", command=orders_window.destroy)
        close_button.pack(pady=10, side="bottom")


    def generate_shopping_list(self):
        shopping_list = []
        current_time = datetime.now()
        
    # Check which ingredients were flagged as needed
        for ingredient, needed in SHOPPING_NEEDED.items():
            if needed:
                current_amount = INGREDIENTS[ingredient]
                shopping_list.append(
                    f"We need to order {MAX_INGREDIENTS - current_amount} units of {ingredient} (Current stock: {current_amount})"
                )
                SHOPPING_NEEDED[ingredient] = False  # Reset flag after adding to list

        if shopping_list:
            content = [
                f"Shopping List - Generated {current_time.strftime('%Y-%m-%d %H:%M:%S')}",
                "____________________"
            ] + shopping_list

            generate_pdf("Shopping_list_1_1.pdf", content)
            messagebox.showinfo("Shopping List", "Shopping list generated. Please check for file: shopping_list_1.pdf")

    
    def update_status_in_tree(self, order_id, status):
        """ Key bit of code called throughout the process_order module."""
        def _update():
            try:
                order_id_str = str(order_id) 
                for item in self.track_tree.get_children():
                    if self.track_tree.item(item, "values")[0] == order_id_str:
                        self.track_tree.item(item, values=(order_id_str, status))
                        return 
            except Exception as e:
                print(f"Error updating tree: {e}")

        self.root.after(0, _update)

    def generate_favourites_report(self):
        """ Code to generate the sorted favourites report pdf """
        favourites = {} # Empty dictionary 
        for order in self.orders.values():
            pizza_name = order['pizza_type'].lower()
            favourites[pizza_name] = favourites.get(pizza_name, 0) + 1

        sorted_favourites = sorted(favourites.items(), key=lambda x: x[1], reverse=True)
        report_lines = [f"{pizza}: Ordered {count} times" for pizza, count in sorted_favourites]
        generate_pdf("favourites_report_1_1.pdf", report_lines)
        messagebox.showinfo("Favourites Report", "Favourites report generated.") # Let the user know the pdf has been generated successfully 


if __name__ == "__main__":
    root = tk.Tk()
    app = PizzaShopApp(root)
    root.mainloop()
