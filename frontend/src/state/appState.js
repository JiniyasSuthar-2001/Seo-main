export const appState = {
  currentProject: null,

  async loadProject() {
    // In a real app, this might fetch from /api/projects or read a cookie/localStorage
    // For this prototype, we'll fetch the first available project or remain empty
    try {
      const res = await fetch('http://localhost:8000/api/projects/');
      const projects = await res.json();
      if (projects.length > 0) {
        this.currentProject = projects[0];
      }
    } catch(e) {
      console.warn("Could not load projects from API", e);
    }
  },

  getCurrentProjectId() {
    return this.currentProject ? this.currentProject.id : null;
  }
};
