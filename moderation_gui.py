import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base URL for your Next.js API
API_BASE_URL = os.getenv("API_BASE_URL", "https://shirli.vercel.app") # Replace with your Vercel deployment URL

class ModerationGUI:
    def __init__(self, master):
        self.master = master
        master.title("Shir-li Moderation GUI")
        master.geometry("1000x800") # Increased window size

        self.requests = []
        self.current_request_index = -1

        # --- Request List Frame ---
        self.request_list_frame = ttk.LabelFrame(master, text="Pending Requests")
        self.request_list_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.tree = ttk.Treeview(self.request_list_frame, columns=("ID", "Title", "Artist", "Type", "Status"), show="headings")
        self.tree.heading("ID", text="Song ID")
        self.tree.heading("Title", text="Title")
        self.tree.heading("Artist", text="Artist")
        self.tree.heading("Type", text="Request Type")
        self.tree.heading("Status", text="Status")

        self.tree.column("ID", width=100, anchor="w")
        self.tree.column("Title", width=200, anchor="w")
        self.tree.column("Artist", width=150, anchor="w")
        self.tree.column("Type", width=100, anchor="w")
        self.tree.column("Status", width=80, anchor="w")

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.on_request_double_click) # Double-click to load details

        self.load_button = ttk.Button(self.request_list_frame, text="Load Pending Requests", command=self.load_pending_requests)
        self.load_button.pack(pady=5)

        # --- Request Details Frame ---
        self.details_frame = ttk.LabelFrame(master, text="Request Details")
        self.details_frame.pack(padx=10, pady=10, fill="x")

        self.fields = {}
        field_names = ["Song ID", "Title", "Artist", "YouTube Link", "Spotify Link", "Tab4u Link", "Tags", "Request Type", "Reason"]
        for i, field in enumerate(field_names):
            row = i // 2
            col = i % 2 * 2
            ttk.Label(self.details_frame, text=f"{field}:").grid(row=row, column=col, padx=5, pady=2, sticky="w")
            if field in ["Tags", "Reason"]:
                entry = scrolledtext.ScrolledText(self.details_frame, height=4, width=40, wrap=tk.WORD)
                entry.grid(row=row, column=col+1, padx=5, pady=2, sticky="ew")
            else:
                entry = ttk.Entry(self.details_frame, width=50)
                entry.grid(row=row, column=col+1, padx=5, pady=2, sticky="ew")
            self.fields[field] = entry
            self.details_frame.grid_columnconfigure(col+1, weight=1) # Make entry columns expandable

        # Add buttons for actions
        self.button_frame = ttk.Frame(self.details_frame)
        self.button_frame.grid(row=len(field_names)//2 + (len(field_names)%2), column=0, columnspan=4, pady=10)

        self.save_button = ttk.Button(self.button_frame, text="Save Edits", command=self.save_edits)
        self.save_button.pack(side="left", padx=5)

        self.approve_button = ttk.Button(self.button_frame, text="Approve Request", command=self.approve_request)
        self.approve_button.pack(side="left", padx=5)

        self.reject_button = ttk.Button(self.button_frame, text="Reject Request", command=self.reject_request)
        self.reject_button.pack(side="left", padx=5)

        self.test_links_button = ttk.Button(self.button_frame, text="Test Links", command=self.test_links)
        self.test_links_button.pack(side="left", padx=5)

        self.clear_details_button = ttk.Button(self.button_frame, text="Clear Details", command=self.clear_details)
        self.clear_details_button.pack(side="left", padx=5)

        self.load_pending_requests() # Load requests on startup

    def clear_details(self):
        for field_name, entry_widget in self.fields.items():
            if isinstance(entry_widget, scrolledtext.ScrolledText):
                entry_widget.delete(1.0, tk.END)
            else:
                entry_widget.delete(0, tk.END)
        self.current_request_index = -1 # No request selected

    def load_pending_requests(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.requests = []
        self.clear_details()

        try:
            response = requests.get(f"{API_BASE_URL}/api/get-pending-requests")
            response.raise_for_status()
            data = response.json()
            self.requests = data.get("requests", [])

            for req in self.requests:
                self.tree.insert("", "end", values=(
                    req.get("Song ID", ""),
                    req.get("Title", ""),
                    req.get("Artist", ""),
                    req.get("Request Type", ""),
                    req.get("Status", "")
                ))
            messagebox.showinfo("Success", f"Loaded {len(self.requests)} pending requests.")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error", f"Failed to fetch requests: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def on_request_double_click(self, event):
        selected_item = self.tree.selection()
        if not selected_item:
            return

        item_id = selected_item[0]
        values = self.tree.item(item_id, "values")
        song_id_to_load = values[0]

        # Find the full request object from self.requests
        for i, req in enumerate(self.requests):
            if req.get("Song ID") == song_id_to_load:
                self.current_request_index = i
                self.populate_details(req)
                break

    def populate_details(self, request_data):
        self.clear_details() # Clear previous details first
        for field_name, entry_widget in self.fields.items():
            value = request_data.get(field_name, "")
            if isinstance(entry_widget, scrolledtext.ScrolledText):
                entry_widget.delete(1.0, tk.END)
                entry_widget.insert(tk.END, value)
            else:
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, value)

    def get_current_details(self):
        details = {}
        for field_name, entry_widget in self.fields.items():
            if isinstance(entry_widget, scrolledtext.ScrolledText):
                details[field_name] = entry_widget.get(1.0, tk.END).strip()
            else:
                details[field_name] = entry_widget.get().strip()
        return details

    def save_edits(self):
        if self.current_request_index == -1:
            messagebox.showwarning("No Request Selected", "Please select a request to save edits for.")
            return

        updated_data = self.get_current_details()
        original_request = self.requests[self.current_request_index]
        request_id = original_request.get("Request ID") # Use Request ID for update

        if not request_id:
            messagebox.showerror("Error", "Request ID is missing for the selected request.")
            return

        try:
            response = requests.post(
                f"{API_BASE_URL}/api/update-request-data",
                json={"requestId": request_id, "updatedData": updated_data}
            )
            response.raise_for_status()
            messagebox.showinfo("Success", "Request data updated successfully!")
            self.load_pending_requests() # Reload to reflect changes
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error", f"Failed to save edits: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def approve_request(self):
        if self.current_request_index == -1:
            messagebox.showwarning("No Request Selected", "Please select a request to approve.")
            return

        request_data = self.get_current_details()
        request_id = self.requests[self.current_request_index].get("Request ID")

        if not request_id:
            messagebox.showerror("Error", "Request ID is missing for the selected request.")
            return

        try:
            response = requests.post(
                f"{API_BASE_URL}/api/approve-request",
                json={"requestId": request_id, "songData": request_data}
            )
            response.raise_for_status()
            messagebox.showinfo("Success", "Request approved and processed!")
            self.load_pending_requests() # Reload to remove approved request
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error", f"Failed to approve request: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def reject_request(self):
        if self.current_request_index == -1:
            messagebox.showwarning("No Request Selected", "Please select a request to reject.")
            return

        request_id = self.requests[self.current_request_index].get("Request ID")

        if not request_id:
            messagebox.showerror("Error", "Request ID is missing for the selected request.")
            return

        try:
            response = requests.post(
                f"{API_BASE_URL}/api/reject-request",
                json={"requestId": request_id}
            )
            response.raise_for_status()
            messagebox.showinfo("Success", "Request rejected!")
            self.load_pending_requests() # Reload to remove rejected request
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error", f"Failed to reject request: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def test_links(self):
        details = self.get_current_details()
        youtube_link = details.get("YouTube Link")
        spotify_link = details.get("Spotify Link")
        tab4u_link = details.get("Tab4u Link")

        results = []

        if youtube_link:
            try:
                response = requests.head(youtube_link, allow_redirects=True, timeout=5)
                results.append(f"YouTube Link ({youtube_link}): {'OK' if response.status_code == 200 else f'Error {response.status_code}'}")
            except requests.exceptions.RequestException as e:
                results.append(f"YouTube Link ({youtube_link}): Failed ({e})")
        else:
            results.append("YouTube Link: Not provided")

        if spotify_link:
            try:
                response = requests.head(spotify_link, allow_redirects=True, timeout=5)
                results.append(f"Spotify Link ({spotify_link}): {'OK' if response.status_code == 200 else f'Error {response.status_code}'}")
            except requests.exceptions.RequestException as e:
                results.append(f"Spotify Link ({spotify_link}): Failed ({e})")
        else:
            results.append("Spotify Link: Not provided")

        if tab4u_link:
            try:
                response = requests.head(tab4u_link, allow_redirects=True, timeout=5)
                results.append(f"Tab4u Link ({tab4u_link}): {'OK' if response.status_code == 200 else f'Error {response.status_code}'}")
            except requests.exceptions.RequestException as e:
                results.append(f"Tab4u Link ({tab4u_link}): Failed ({e})")
        else:
            results.append("Tab4u Link: Not provided")

        messagebox.showinfo("Link Test Results", "\n".join(results))

if __name__ == "__main__":
    root = tk.Tk()
    app = ModerationGUI(root)
    root.mainloop()
